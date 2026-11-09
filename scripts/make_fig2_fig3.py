"""Paper figures that are not produced by the model notebooks: Fig. 2 (data description) and Fig. 3 (mean load
and test MAE by hour of day; file name fig4_rq2_hour_profile.png).

Usage:
    python make_fig2_fig3.py SESSIONS.xlsx RQ2_COMBINED_PREDICTIONS.csv [OUT_DIR]

SESSIONS.xlsx = acn_data(cleaned).xlsx (sheet full_data); RQ2_COMBINED_PREDICTIONS.csv = output of the rq2_aggregate
notebook. The plotting code is the code of the figure cells used for the paper (taken from the notebooks of the
2026-10-23 version), only wrapped into one script. Needs pandas, numpy, matplotlib, seaborn, openpyxl.
"""
import os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

if len(sys.argv) < 3:
    sys.exit(__doc__)
OUT_DIR = sys.argv[3] if len(sys.argv) > 3 else '.'
os.makedirs(OUT_DIR, exist_ok=True)
df = pd.read_excel(sys.argv[1], sheet_name='full_data')
df['connectionTime'] = pd.to_datetime(df['connectionTime'])
COMB = pd.read_csv(sys.argv[2], parse_dates=['time'])

# ===== PAPER FIGURES: style chung (seaborn + matplotlib), giữ nhất quán giữa các notebook =====
import seaborn as sns
OKABE = {'blue': '#0072B2', 'orange': '#E69F00', 'green': '#009E73', 'red': '#D55E00', 'purple': '#CC79A7', 'sky': '#56B4E9', 'yellow': '#F0E442', 'grey': '#7F7F7F', 'black': '#222222'}
sns.set_theme(context='paper', style='ticks', font='DejaVu Sans', rc={
    'font.size': 7, 'axes.titlesize': 7.5, 'axes.labelsize': 7, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5,
    'legend.fontsize': 6.5, 'legend.frameon': False, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
    'lines.linewidth': 1.2, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'figure.dpi': 110, 'savefig.dpi': 300})
FIG_DIR = os.path.join(OUT_DIR, 'paper_figures'); os.makedirs(FIG_DIR, exist_ok=True)
def panel_tag(ax, s):                                  # nhãn (a), (b), ... ở góc trên trái, như bài báo
    ax.text(-0.02, 1.08, s, transform=ax.transAxes, fontsize=8, fontweight='bold', va='bottom', ha='right')
def save_paper_fig(fig, name):
    p = os.path.join(FIG_DIR, name + '.png'); fig.savefig(p, bbox_inches='tight', pad_inches=0.03); print('Đã lưu', p)


# ===== Fig. 2 của bài báo: mô tả dữ liệu từ bảng df gốc =====
d = df[['siteID', 'connectionTime', 'kWhDelivered']].copy()
d['siteID'] = d['siteID'].astype(int); d['hour_i'] = d.connectionTime.dt.hour
d['day_type'] = np.where(d.connectionTime.dt.dayofweek >= 5, 'Weekend', 'Weekday')
SITES_ALL = sorted(d.siteID.unique()); SITE_COL = dict(zip(SITES_ALL, [OKABE['blue'], OKABE['red'], OKABE['green']]))
print(d.groupby(['siteID', 'day_type']).size().unstack().to_string())          # site 19 gần như không có phiên cuối tuần -> chỉ vẽ site 1, 2 ở (a), (b)
share = d[d.siteID.isin([1, 2])].groupby(['siteID', 'day_type', 'hour_i']).size().rename('n').reset_index()
share['share'] = 100 * share.n / share.groupby(['siteID', 'day_type']).n.transform('sum')
share['Site'] = 'Site ' + share.siteID.astype(str)
share.to_csv(os.path.join(FIG_DIR, 'fig2_arrival_share_by_hour.csv'), index=False)
fig, ax = plt.subplots(1, 3, figsize=(4.8, 1.7), gridspec_kw={'width_ratios': [1, 1, 0.8], 'wspace': 0.34})
for a, dt in zip(ax[:2], ['Weekday', 'Weekend']):
    sns.lineplot(data=share[share.day_type == dt], x='hour_i', y='share', hue='Site', hue_order=['Site 1', 'Site 2'],
                 palette={'Site 1': SITE_COL[1], 'Site 2': SITE_COL[2]}, marker='o', markersize=2.4, markeredgewidth=0, dashes=False, ax=a, legend=(dt == 'Weekday'))
    a.set_title(dt); a.set_xlabel('Arrival hour'); a.set_xticks([0, 6, 12, 18, 23]); a.set_ylim(0, 27)
    a.set_ylabel('Share of sessions, %' if dt == 'Weekday' else '')
if ax[0].get_legend() is not None: ax[0].get_legend().set_title(None); sns.move_legend(ax[0], 'upper right', handlelength=1.2, labelspacing=0.2, borderaxespad=0.1)
sns.boxplot(data=d, y='siteID', x='kWhDelivered', hue='siteID', order=SITES_ALL, hue_order=SITES_ALL, palette=SITE_COL, orient='h', ax=ax[2],
            showfliers=False, linewidth=0.6, width=0.55, saturation=1, legend=False, whis=(5, 95))
ax[2].set_yticks(range(len(SITES_ALL))); ax[2].set_yticklabels([f'Site {s}\nn={int((d.siteID == s).sum()):,}' for s in SITES_ALL], fontsize=5.8); ax[2].set_ylabel('')
ax[2].set_xlabel('Energy per session, kWh'); ax[2].set_title('Energy'); ax[2].set_xlim(0, 45)
for a, t in zip(ax, 'abc'): panel_tag(a, f'({t})')
save_paper_fig(fig, 'fig2_data_description'); plt.show()


# ===== Fig. 4 của bài báo: tải trung bình theo giờ và MAE theo giờ (H = 24, Test, run 1), tính từ COMB của notebook này =====
SHORT = {'Seasonal Naive': 'Seasonal naive', 'Persistence (tuned)': 'Persistence', 'LSTM': 'LSTM', 'Hybrid': 'Hybrid'}
MCOL = {'Seasonal naive': OKABE['grey'], 'Persistence': OKABE['orange'], 'LSTM': OKABE['blue'], 'Hybrid': OKABE['red']}
Tt = COMB[(COMB.split == 'test') & (COMB.run == 'run1') & (COMB.horizon == 24)].copy()
Tt['hour'] = Tt.time.dt.hour; Tt['abs_err'] = (Tt.pred - Tt.actual).abs(); Tt['Model'] = Tt.model.map(SHORT)
LOAD = Tt[Tt.model == 'Hybrid'].groupby(['site', 'hour']).actual.mean().rename('mean_load').reset_index()
MAEH = Tt.groupby(['site', 'Model', 'hour']).abs_err.mean().rename('mae').reset_index()
LOAD.to_csv(os.path.join(OUT_DIR, 'fig4_hour_load.csv'), index=False); MAEH.to_csv(os.path.join(OUT_DIR, 'fig4_hour_mae_h24.csv'), index=False)
# ---- vẽ (chỉ cần LOAD và MAEH) ----
sites_ = sorted(LOAD.site.unique())
fig, ax = plt.subplots(2, len(sites_), figsize=(4.8, 2.6), sharex=True, squeeze=False, gridspec_kw={'hspace': 0.32, 'wspace': 0.28})
for j, s in enumerate(sites_):
    sns.barplot(data=LOAD[LOAD.site == s], x='hour', y='mean_load', color='#BDBDBD', width=0.85, ax=ax[0, j])
    ax[0, j].set_title(f'Site {s}'); ax[0, j].set_ylabel('Mean load, kWh/h' if j == 0 else ''); ax[0, j].set_xlabel('')
    sns.lineplot(data=MAEH[MAEH.site == s], x='hour', y='mae', hue='Model', hue_order=list(MCOL), palette=MCOL, ax=ax[1, j], legend=False)
    ax[1, j].set_ylabel('Test MAE, kWh/h' if j == 0 else ''); ax[1, j].set_xlabel('Hour of day'); ax[1, j].set_ylim(bottom=0)
    ax[1, j].set_xticks([0, 6, 12, 18, 23]); ax[0, j].set_xticks([0, 6, 12, 18, 23]); ax[0, j].set_xticklabels([0, 6, 12, 18, 23])
fig.legend(handles=[plt.Line2D([], [], color=c, lw=1.4) for c in MCOL.values()], labels=list(MCOL), loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.13), fontsize=6)
panel_tag(ax[0, 0], '(a)'); panel_tag(ax[0, 1], '(b)'); panel_tag(ax[1, 0], '(c)'); panel_tag(ax[1, 1], '(d)')
save_paper_fig(fig, 'fig4_rq2_hour_profile'); plt.show()
