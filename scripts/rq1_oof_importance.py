import numpy as np, pandas as pd, json, warnings, sys, os
warnings.filterwarnings('ignore')
HERE=os.path.dirname(os.path.abspath(__file__))
src=open(os.path.join(HERE,'rq1_group_importance_v3.py'),encoding='utf8').read()
head=src[:src.index("rows=[];base={}")]
exec(head)   # data, models, helpers (mk, fit fns, G, cols_of, pred, DEV, TEST, y, df)
OUT=os.environ.get('RQ1_OUT','.')+os.sep   # folder for the result files
FOLDS=[('2018-01-01','2019-03-15','2019-05-15'),('2018-01-01','2019-05-15','2019-07-15'),('2018-01-01','2019-07-15','2019-09-15'),('2018-01-01','2019-09-15','2019-11-15'),('2018-01-01','2019-11-15','2020-01-15')]
t=df.connectionTime; day=t.dt.normalize().to_numpy()
NREP=20; NB=1000; rng=np.random.default_rng(0)
ORDER=list(G)
def perm_cols(Xv,cs,idx):
    Z=Xv.copy()
    for c in cs:
        v=Xv[c].to_numpy()[idx]
        Z[c]=pd.Categorical(v,categories=Xv[c].cat.categories) if hasattr(Xv[c],'cat') else v
    return Z
def cell_keys(Xv,g,kind):
    oth=[c for g2 in G if g2!=g for c in G[g2]]
    k=pd.DataFrame(index=Xv.index)
    for c in oth:
        v=Xv[c]
        if c in('hour_sin','hour_cos'): continue
        k[c]=v.astype(str).to_numpy()
    k['hr']=np.floor(df.hour.to_numpy()[Xv.index]).astype(int) if g!='hour' else 0
    return k.astype(str).agg('|'.join,axis=1).to_numpy()
res={}
for name,(kind,fit) in MODELS.items():
    X=mk(kind); per_fold=[]
    for (a,b,c) in FOLDS:
        tr=np.flatnonzero((t<pd.Timestamp(b)+pd.Timedelta(days=1)).values) if False else np.flatnonzero((t<pd.Timestamp(b)+pd.Timedelta(days=1)).values)
        va=np.flatnonzero(((t>=pd.Timestamp(b)+pd.Timedelta(days=1))&(t<pd.Timestamp(c)+pd.Timedelta(days=1))).values)
        m=fit(X.iloc[tr],y[tr]); Xv=X.iloc[va]; yv=y[va]
        base=(pred(m,Xv)-yv)**2
        d=dict(va=va,base=base,perm={},cond={})
        for g in G:
            cs=cols_of(kind,g); sq=np.zeros(len(va))
            for r in range(NREP):
                sq+=(pred(m,perm_cols(Xv,cs,rng.permutation(len(va))))-yv)**2
            d['perm'][g]=sq/NREP
            keys=cell_keys(Xv,g,kind); u,inv=np.unique(keys,return_inverse=True)
            sqc=np.zeros(len(va))
            for r in range(NREP):
                idx=np.arange(len(va))
                for cid in range(len(u)):
                    w=np.flatnonzero(inv==cid)
                    if len(w)>1: idx[w]=rng.permutation(w)
                sqc+=(pred(m,perm_cols(Xv,cs,idx))-yv)**2
            d['cond'][g]=sqc/NREP
        per_fold.append(d); print(name,'fold',a,b,len(tr),len(va),flush=True)
    # point estimates: mean over folds of % rise
    def rise(sub,which,g):
        return 100*(np.sqrt(sub['perm' if which=='p' else 'cond'][g].mean())/np.sqrt(sub['base'].mean())-1)
    pt={g:np.mean([rise(f,'p',g) for f in per_fold]) for g in G}
    ptc={g:np.mean([rise(f,'c',g) for f in per_fold]) for g in G}
    # bootstrap days within each fold
    B=np.zeros((NB,len(G))); 
    dd=[]
    for f in per_fold:
        days=day[f['va']]; ud,inv=np.unique(days,return_inverse=True)
        nd=len(ud); cnt=np.bincount(inv); sb=np.bincount(inv,weights=f['base'])
        sp={g:np.bincount(inv,weights=f['perm'][g]) for g in G}
        dd.append((nd,cnt,sb,sp))
    for bi in range(NB):
        acc=np.zeros(len(G))
        for (nd,cnt,sb,sp) in dd:
            w=np.bincount(rng.integers(0,nd,nd),minlength=nd)
            n=(w*cnt).sum(); rb=np.sqrt((w*sb).sum()/n)
            for gi,g in enumerate(G): acc[gi]+=100*(np.sqrt((w*sp[g]).sum()/n)/rb-1)
        B[bi]=acc/len(dd)
    lo,hi=np.percentile(B,2.5,axis=0),np.percentile(B,97.5,axis=0)
    ordpt=tuple(np.argsort(-np.array([pt[g] for g in G])))
    kept=np.mean([tuple(np.argsort(-B[i]))==ordpt for i in range(NB)])*100
    tot=sum(max(pt[g],0) for g in G)
    res[name]=dict(point=pt,lo=dict(zip(G,lo)),hi=dict(zip(G,hi)),cond=ptc,order_kept=kept,order=[ORDER[i] for i in ordpt],share_top2=(pt['location']+pt['hour'])/tot*100)
    print(name,json.dumps(res[name]),flush=True)
json.dump(res,open(OUT+'table3_oof.json','w'),indent=1)
# share of sessions at site 1: out-of-fold (all val windows) vs test
va_all=np.concatenate([np.flatnonzero(((t>=pd.Timestamp(b)+pd.Timedelta(days=1))&(t<pd.Timestamp(c)+pd.Timedelta(days=1))).values) for (a,b,c) in FOLDS])
print('site1 share oof',(df.siteID.iloc[va_all]==1).mean(),'test',(df.siteID.iloc[TEST]==1).mean())
