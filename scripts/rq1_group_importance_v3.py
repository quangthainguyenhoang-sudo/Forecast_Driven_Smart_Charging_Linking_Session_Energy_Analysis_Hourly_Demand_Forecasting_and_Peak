import numpy as np, pandas as pd, json, warnings, sys, os
warnings.filterwarnings('ignore')
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, SplineTransformer
from sklearn.linear_model import Lasso
import xgboost as xgb, lightgbm as lgb
SEED=42; TARGET='kWhDelivered'
FEATURES=['siteID','stationID','hour_sin','hour_cos','day_of_week','is_weekend','is_holiday','month','seasonal']
CAT=['siteID','stationID','day_of_week','month','seasonal']
G={'hour':['hour_sin','hour_cos'],'day_of_week':['day_of_week','is_weekend'],'location':['siteID','stationID'],'month':['month','seasonal'],'holiday':['is_holiday']}
P=os.environ.get('ACN_XLSX','acn_data(cleaned)_v3_kaggle.xlsx')   # path of the cleaned session table (set ACN_XLSX to change)
try: df=pd.read_excel(P,sheet_name='full_data')
except ValueError: df=pd.read_excel(P)
df=df.sort_values('connectionTime',kind='stable').reset_index(drop=True)
if 'hour' not in df: ct=df.connectionTime; df['hour']=ct.dt.hour+ct.dt.minute/60+ct.dt.second/3600
LEV={'day_of_week':list(range(7)),'month':list(range(1,13)),'seasonal':list(range(4)),'siteID':sorted(df.siteID.unique()),'stationID':sorted(df.stationID.unique())}
t=df.connectionTime
tr_end=pd.Timestamp('2019-10-31')+pd.Timedelta(days=1); va_end=pd.Timestamp('2020-01-15')+pd.Timedelta(days=1); te_end=pd.Timestamp('2021-09-13')+pd.Timedelta(days=1)
DEV=np.flatnonzero((t<va_end).values); TEST=np.flatnonzero(((t>=va_end)&(t<te_end)).values)
y=df[TARGET].to_numpy(float)
def mk(kind):
    X=df[FEATURES].copy()
    for c in CAT: X[c]=pd.Categorical(df[c],categories=LEV[c])
    if kind=='lr':
        for c in CAT: X[c]=X[c].astype(object)
        X['_h']=df.hour.to_numpy(float)
    return X
def const_cols(X,cols,ref):
    X=X.copy()
    for c in cols:
        if c=='_h': X[c]=ref[c].iloc[0] if hasattr(ref[c],'iloc') else ref[c]
        else: X[c]=ref[c].iloc[0]
    return X
def lr_fit(X,yy):
    # tuned config of linear-regression notebook (v3 rerun): elasticnet alpha=0.0011210982723531943, l1_ratio=0.6866638734356715,
    # station_level=True, hour_repr=sincos, interactions=True, scale=True, drop_first=True
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import ElasticNet
    def add(X):
        X=X.copy(); X['_sh']=X.siteID.astype(str)+'|'+np.floor(X['_h']).astype(int).astype(str); return X
    pre=ColumnTransformer([('oh',OneHotEncoder(handle_unknown='ignore',sparse_output=False,drop='first'),['siteID','day_of_week','month','seasonal','stationID']),
        ('num',StandardScaler(),['hour_sin','hour_cos','is_weekend','is_holiday']),
        ('inter',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['_sh'])],remainder='drop',sparse_threshold=0)
    p=Pipeline([('pre',pre),('est',ElasticNet(alpha=0.0011210982723531943,l1_ratio=0.6866638734356715,max_iter=20000,random_state=SEED))]).fit(add(X),yy)
    class W:
        def predict(s,Z): return p.predict(add(Z))
    return W()
def xgb_fit(X,yy):
    m=xgb.XGBRegressor(n_estimators=950,learning_rate=0.00706529795743501,max_depth=8,min_child_weight=2,subsample=0.8169721934294589,colsample_bytree=0.9555790920363825,colsample_bylevel=0.6452002693112355,gamma=1.242615754539959e-8,reg_alpha=0.0014710926918588484,reg_lambda=0.006304363224086794,grow_policy='lossguide',max_leaves=13,max_cat_to_onehot=13,max_bin=256,objective='reg:squarederror',random_state=SEED,n_jobs=-1,tree_method='hist',enable_categorical=True,verbosity=0)
    return m.fit(X,yy)
def lgb_fit(X,yy):
    m=lgb.LGBMRegressor(n_estimators=350,learning_rate=0.016457,num_leaves=10,max_depth=5,min_child_samples=39,subsample=0.608259,subsample_freq=1,colsample_bytree=0.910422,reg_alpha=0.00074,reg_lambda=7.897344,min_split_gain=0.23136,cat_smooth=3.7989,cat_l2=1.27738,max_cat_threshold=31,objective='regression',random_state=SEED,n_jobs=2,deterministic=True,force_row_wise=True,verbosity=-1)
    return m.fit(X,yy)
MODELS={'Linear regression':('lr',lr_fit),'XGBoost':('xgb',xgb_fit),'LightGBM':('lgb',lgb_fit)}
def cols_of(kind,g):
    c=list(G[g]); 
    if kind=='lr' and g=='hour': c.append('_h')
    return c
def setc(X,c):
    v=X[c].iloc[0]
    if hasattr(X[c],'cat'): X[c]=pd.Categorical([v]*len(X),categories=X[c].cat.categories)
    else: X[c]=v
def pred(m,X): return np.clip(m.predict(X),0,None)
rows=[];base={}
rng=np.random.default_rng(0)
NREP=20
for name,(kind,fit) in MODELS.items():
    X=mk(kind); Xd,Xt=X.iloc[DEV],X.iloc[TEST]; yt=y[TEST]
    m=fit(Xd,y[DEV]); p=pred(m,Xt)
    r2=r2_score(yt,p); rm=np.sqrt(mean_squared_error(yt,p)); mae=mean_absolute_error(yt,p)
    base[name]=dict(R2=r2,RMSE=rm,MAE=mae); print(name,base[name],flush=True)
    for g in G:
        cs=cols_of(kind,g); drs=[];dls=[]
        for r in range(NREP):
            idx=rng.permutation(len(Xt)); Z=Xt.copy()
            for c in cs: Z[c]=Xt[c].to_numpy()[idx] if not hasattr(Xt[c],'cat') else pd.Categorical(Xt[c].to_numpy()[idx],categories=Xt[c].cat.categories)
            pz=pred(m,Z); drs.append(r2-r2_score(yt,pz)); dls.append(np.sqrt(mean_squared_error(yt,pz))-rm)
        # drop group: constant columns in train+test
        Xdrop=X.copy()
        for c in cs: setc(Xdrop,c)
        md=fit(Xdrop.iloc[DEV],y[DEV]); r2_drop=r2_score(yt,pred(md,Xdrop.iloc[TEST]))
        # only group: others constant
        Xon=X.copy()
        for g2 in G:
            if g2!=g:
                for c in cols_of(kind,g2): setc(Xon,c)
        mo=fit(Xon.iloc[DEV],y[DEV]); r2_only=r2_score(yt,pred(mo,Xon.iloc[TEST]))
        rows.append(dict(model=name,group=g,perm_R2_loss=np.mean(drs),perm_R2_sd=np.std(drs),perm_RMSE_gain=np.mean(dls),R2_drop=r2_drop,R2_only=r2_only))
        print(rows[-1],flush=True)
res=pd.DataFrame(rows); res.to_csv(os.path.join(os.environ.get('RQ1_OUT','.'),'group_importance.csv'),index=False)
json.dump(base,open(os.path.join(os.environ.get('RQ1_OUT','.'),'base_test.json'),'w'))
