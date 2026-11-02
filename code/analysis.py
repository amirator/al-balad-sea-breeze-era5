"""Al-Balad afternoon sea-breeze analysis, 1940-2025 (ERA5 via Open-Meteo).
Run from the paper folder:  python code/analysis.py
All numbers quoted in the paper are written to tables/ and results.json by this script."""
import json, math, os, io, pathlib
import numpy as np, pandas as pd, requests
import pymannkendall as mk
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, FIG, TAB = ROOT/"data", ROOT/"figures", ROOT/"tables"
for p in (DATA, FIG, TAB): p.mkdir(exist_ok=True)
RAW = DATA/"openmeteo_era5_albalad_1940_2025.json"
URL = ("https://archive-api.open-meteo.com/v1/archive?latitude=21.485&longitude=39.186"
       "&start_date=1940-01-01&end_date=2025-12-31&hourly=wind_speed_10m,wind_direction_10m"
       "&models=era5&wind_speed_unit=ms&timezone=Asia%2FRiyadh")
ALBALAD = (21.4847, 39.1867)   # approx. centre of the Historic Jeddah property (Al-Balad)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "figure.dpi": 150})

if not RAW.exists():
    RAW.write_bytes(requests.get(URL, timeout=600).content)
meta = json.loads(RAW.read_text())
h = pd.DataFrame(meta["hourly"]); h["time"] = pd.to_datetime(h["time"])
h = h.rename(columns={"wind_speed_10m": "ws", "wind_direction_10m": "wd"})
h["year"], h["month"], h["hour"] = h.time.dt.year, h.time.dt.month, h.time.dt.hour
R = {"grid_lat": meta["latitude"], "grid_lon": meta["longitude"], "grid_elev_m": meta["elevation"],
     "n_hours": int(len(h)), "n_missing_wd": int(h.wd.isna().sum()), "n_missing_ws": int(h.ws.isna().sum()),
     "first": str(h.time.min()), "last": str(h.time.max())}
h = h.dropna(subset=["wd", "ws"])
AFT = h[h.hour.between(13, 17)].copy()          # 13:00-17:00 local time (UTC+3)
EARLY, RECENT = (1940, 1969), (1996, 2025)

def in_sector(wd, lo, hi):  # inclusive sector lo..hi degrees (from), hi may be 360
    return (wd >= lo) & (wd <= hi)

def share(df, lo=270, hi=360): return in_sector(df.wd, lo, hi).mean()

# ---- annual series, main definition: 270-360 deg (W through N) ----
ann = AFT.groupby("year").apply(lambda d: pd.Series({
    "share_W_NW": share(d), "mean_ws": d.ws.mean(),
    "mean_ws_onshore": d.loc[in_sector(d.wd, 270, 360), "ws"].mean(),
    "share_calm_lt2": (d.ws < 2).mean()}), include_groups=False)
ann.to_csv(TAB/"annual_afternoon_series.csv", float_format="%.5f")

def trend(series):
    s = series.dropna().values
    o, m = mk.original_test(s), mk.hamed_rao_modification_test(s)
    return dict(n=len(s), tau=o.Tau, p_mk=o.p, p_hr=m.p, sen_per_decade=o.slope*10)

rows = []
for name, col, scale in [("Afternoon W-N share (270-360°), % of hours", "share_W_NW", 100),
                         ("Afternoon mean wind speed, m/s", "mean_ws", 1),
                         ("Afternoon onshore (270-360°) mean speed, m/s", "mean_ws_onshore", 1),
                         ("Afternoon calm/light (<2 m/s) share, % of hours", "share_calm_lt2", 100)]:
    for per in [(1940, 2025), (1950, 2025), (1979, 2025)]:
        t = trend(ann.loc[per[0]:per[1], col] * scale)
        rows.append({"variable": name, "period": f"{per[0]}-{per[1]}", **t})
trend_tab = pd.DataFrame(rows); trend_tab.to_csv(TAB/"table2a_trend_tests.csv", index=False, float_format="%.4f")

# ---- decade comparison ----
AFT["decade"] = (AFT.year // 10) * 10
dec = AFT.groupby("decade").apply(lambda d: pd.Series({
    "years": f"{d.year.min()}-{d.year.max()}", "afternoon_hours": len(d),
    "share_W_N_pct": 100*share(d), "share_NW_pct(292.5-337.5)": 100*share(d, 292.5, 337.5),
    "mean_ws": d.ws.mean(), "onshore_ws": d.loc[in_sector(d.wd, 270, 360), "ws"].mean(),
    "circular_mean_dir": (np.degrees(np.arctan2(np.sin(np.radians(d.wd)).mean(), np.cos(np.radians(d.wd)).mean())) % 360)}),
    include_groups=False)
dec.to_csv(TAB/"table2b_decades.csv", float_format="%.2f")

# ---- sensitivity across direction thresholds ----
sectors = {"W-N 270-360° (main)": (270, 360), "WSW-NNW 247.5-337.5°": (247.5, 337.5),
           "SW-N 225-360°": (225, 360), "W-NW 270-337.5°": (270, 337.5), "NW only 292.5-337.5°": (292.5, 337.5),
           "Coast-normal ±45° (250-340°)": (250, 340)}
srows = []
for lab, (lo, hi) in sectors.items():
    s = AFT.groupby("year").wd.apply(lambda w: in_sector(w, lo, hi).mean()*100)
    t = trend(s)
    e = in_sector(AFT[AFT.year.between(*EARLY)].wd, lo, hi).mean()*100
    r = in_sector(AFT[AFT.year.between(*RECENT)].wd, lo, hi).mean()*100
    srows.append({"sector": lab, "early_1940_69_pct": e, "recent_1996_2025_pct": r, "diff_pp": r-e,
                  "sen_pp_per_decade": t["sen_per_decade"], "p_mk": t["p_mk"], "p_hamed_rao": t["p_hr"]})
# afternoon-window sensitivity
for lab, (a, b) in {"window 12-16 h": (12, 16), "window 14-18 h": (14, 18)}.items():
    W = h[h.hour.between(a, b)]
    s = W.groupby("year").wd.apply(lambda w: in_sector(w, 270, 360).mean()*100); t = trend(s)
    e = in_sector(W[W.year.between(*EARLY)].wd, 270, 360).mean()*100
    r = in_sector(W[W.year.between(*RECENT)].wd, 270, 360).mean()*100
    srows.append({"sector": f"W-N 270-360°, {lab}", "early_1940_69_pct": e, "recent_1996_2025_pct": r, "diff_pp": r-e,
                  "sen_pp_per_decade": t["sen_per_decade"], "p_mk": t["p_mk"], "p_hamed_rao": t["p_hr"]})
sens = pd.DataFrame(srows); sens.to_csv(TAB/"table3_sensitivity.csv", index=False, float_format="%.4f")

# ---- data summary ----
summ = pd.DataFrame([
    ["Source", "ERA5 reanalysis via Open-Meteo Historical Weather API (models=era5)"],
    ["Grid point returned", f"{R['grid_lat']}° N, {R['grid_lon']}° E (elev. {R['grid_elev_m']:.0f} m)"],
    ["Period", f"{R['first'][:10]} to {R['last'][:10]} (local time, UTC+3)"],
    ["Hourly records", f"{R['n_hours']:,}"],
    ["Missing direction / speed values", f"{R['n_missing_wd']} / {R['n_missing_ws']}"],
    ["Afternoon records (13:00-17:00)", f"{len(AFT):,}"],
    ["Afternoon mean speed, all years", f"{AFT.ws.mean():.2f} m/s"],
    ["Afternoon W-N (270-360°) share, all years", f"{100*share(AFT):.1f}%"],
    ["All-hours W-N share, all years", f"{100*share(h):.1f}%"]], columns=["Item", "Value"])
summ.to_csv(TAB/"table1_data_summary.csv", index=False)

e_df, r_df = AFT[AFT.year.between(*EARLY)], AFT[AFT.year.between(*RECENT)]
R.update({"aft_hours": int(len(AFT)), "aft_share_all": 100*share(AFT), "allhours_share": 100*share(h),
          "early_share": 100*share(e_df), "recent_share": 100*share(r_df),
          "early_ws": e_df.ws.mean(), "recent_ws": r_df.ws.mean(),
          "early_onshore_ws": e_df.loc[in_sector(e_df.wd, 270, 360), "ws"].mean(),
          "recent_onshore_ws": r_df.loc[in_sector(r_df.wd, 270, 360), "ws"].mean(),
          "ann_min_year": int(ann.share_W_NW.idxmin()), "ann_min": 100*ann.share_W_NW.min(),
          "ann_max_year": int(ann.share_W_NW.idxmax()), "ann_max": 100*ann.share_W_NW.max(),
          "y1940": 100*ann.share_W_NW.loc[1940], "y2025": 100*ann.share_W_NW.loc[2025],
          "ann_sd": 100*ann.share_W_NW.std()})
# hour-of-day and month stats
hr = h.groupby(["hour"]).wd.apply(lambda w: in_sector(w, 270, 360).mean()*100)
R["diurnal_max_hour"], R["diurnal_max"] = int(hr.idxmax()), float(hr.max())
R["diurnal_min_hour"], R["diurnal_min"] = int(hr.idxmin()), float(hr.min())
mon = AFT.groupby("month").wd.apply(lambda w: in_sector(w, 270, 360).mean()*100)
R["month_min"], R["month_min_val"] = int(mon.idxmin()), float(mon.min())
R["month_max"], R["month_max_val"] = int(mon.idxmax()), float(mon.max())
monE = e_df.groupby("month").wd.apply(lambda w: in_sector(w, 270, 360).mean()*100)
monR = r_df.groupby("month").wd.apply(lambda w: in_sector(w, 270, 360).mean()*100)
R["month_diff"] = {int(k): float(v) for k, v in (monR - monE).items()}
pd.DataFrame({"early": monE, "recent": monR, "diff": monR-monE}).to_csv(TAB/"monthly_early_recent.csv", float_format="%.2f")
R["trend_main"] = trend_tab.iloc[0].to_dict()
(ROOT/"results.json").write_text(json.dumps(R, indent=2, default=float))

# ================= FIGURES =================
# Fig 1: map with OSM tiles and ERA5 cell
def deg2num(lat, lon, z):
    n = 2**z; x = (lon+180)/360*n; y = (1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n; return x, y
def num2deg(x, y, z):
    n = 2**z; lon = x/n*360-180; lat = math.degrees(math.atan(math.sinh(math.pi*(1-2*y/n)))); return lat, lon
z = 11; lat0, lat1, lon0, lon1 = 21.30, 21.70, 39.02, 39.42
x0, y0 = map(int, deg2num(lat1, lon0, z)); x1, y1 = map(int, deg2num(lat0, lon1, z))
tdir = DATA/"osm_tiles"; tdir.mkdir(exist_ok=True)
mosaic = Image.new("RGB", ((x1-x0+1)*256, (y1-y0+1)*256))
for x in range(x0, x1+1):
    for y in range(y0, y1+1):
        f = tdir/f"{z}_{x}_{y}.png"
        if not f.exists():
            f.write_bytes(requests.get(f"https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                          headers={"User-Agent": "AlBaladSeaBreezePaper/1.0 (academic, non-commercial)"}, timeout=60).content)
        mosaic.paste(Image.open(f).convert("RGB"), ((x-x0)*256, (y-y0)*256))
N, W_ = num2deg(x0, y0, z); S, E = num2deg(x1+1, y1+1, z)
fig, ax = plt.subplots(figsize=(6, 6))
ax.imshow(mosaic, extent=[W_, E, S, N], aspect=1/math.cos(math.radians(21.5)))
g = (R["grid_lat"], R["grid_lon"])
ax.add_patch(plt.Rectangle((g[1]-0.125, g[0]-0.125), 0.25, 0.25, fill=False, ec="crimson", lw=2, ls="--",
             label="ERA5 cell (0.25° × 0.25°)"))
ax.plot(g[1], g[0], "x", color="crimson", ms=9, mew=2, label=f"ERA5 grid point {g[0]}° N, {g[1]}° E")
ax.plot(ALBALAD[1], ALBALAD[0], "o", color="navy", ms=8, label="Al-Balad (Historic Jeddah)")
ax.annotate("", xy=(39.11, 21.62), xytext=(39.05, 21.66), arrowprops=dict(arrowstyle="->", color="k", lw=2))
ax.text(39.03, 21.675, "NW afternoon\nsea breeze", fontsize=8)
ax.set_xlim(lon0, lon1); ax.set_ylim(lat0, lat1); ax.set_xlabel("Longitude (° E)"); ax.set_ylabel("Latitude (° N)")
ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
ax.text(lon1-0.005, lat0+0.003, "Basemap © OpenStreetMap contributors (ODbL)", fontsize=6, ha="right", va="bottom",
        bbox=dict(fc="white", ec="none", alpha=.8))
fig.tight_layout(); fig.savefig(FIG/"fig1_map.png", dpi=200); plt.close(fig)

# Fig 2: rawshan photo (CC BY-SA 4.0) – resized copy
SRC = FIG/"rawasheen_source.jpg"
if not SRC.exists():
    SRC.write_bytes(requests.get("https://commons.wikimedia.org/w/index.php?title=Special:FilePath/"
        "Rawasheen;_A_Model_of_Traditional_Saudi_Wooden_Architecture_in_Historic_Jeddah,_Saudi_Arabia_(2025).jpg&width=1600",
        headers={"User-Agent": "AlBaladSeaBreezePaper/1.0 (academic)"}, timeout=120).content)
im = Image.open(SRC); im.thumbnail((1400, 1400)); im.save(FIG/"fig2_rawasheen.jpg", quality=88)

# Fig 3: wind roses early vs recent (afternoon)
bins = np.arange(-11.25, 360, 22.5); labels16 = np.arange(0, 360, 22.5)
sp_edges = [0, 2, 4, 6, 8, 99]; sp_lab = ["<2", "2-4", "4-6", "6-8", "≥8 m/s"]
cols = plt.cm.viridis(np.linspace(0.1, 0.95, len(sp_lab)))
fig, axs = plt.subplots(1, 2, subplot_kw={"projection": "polar"}, figsize=(8, 4.2))
for ax, (lab, d) in zip(axs, [(f"{EARLY[0]}-{EARLY[1]}", e_df), (f"{RECENT[0]}-{RECENT[1]}", r_df)]):
    sect = (((d.wd + 11.25) % 360) // 22.5).astype(int)
    base = np.zeros(16)
    for i in range(len(sp_lab)):
        m = (d.ws >= sp_edges[i]) & (d.ws < sp_edges[i+1])
        v = np.bincount(sect[m], minlength=16)/len(d)*100
        ax.bar(np.radians(labels16), v, width=np.radians(20), bottom=base, color=cols[i], edgecolor="w", lw=.3,
               label=sp_lab[i]); base += v
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1); ax.set_title(lab + " (13-17 h)", pad=12)
    ax.set_rlim(0, 32); ax.set_rticks([10, 20, 30]); ax.set_yticklabels(["10%", "20%", "30%"], fontsize=7)
axs[1].legend(loc="center left", bbox_to_anchor=(1.1, 0.5), fontsize=7, title="Speed")
fig.tight_layout(); fig.savefig(FIG/"fig3_windrose.png", dpi=200); plt.close(fig)

# Fig 4: annual series with Sen slope
s = ann.share_W_NW*100; o = mk.original_test(s.values)
fig, ax = plt.subplots(figsize=(7, 3.4))
ax.plot(s.index, s.values, color="steelblue", lw=1, marker="o", ms=2.5, label="Annual share")
ax.plot(s.index, s.rolling(11, center=True).mean(), color="k", lw=1.6, label="11-yr centred mean")
x = np.arange(len(s)); ax.plot(s.index, o.intercept + o.slope*x, "r--", lw=1.4,
        label=f"Sen slope {o.slope*10:+.2f} pp/decade (MK p={o.p:.2f})")
ax.axvspan(1940, 1949.5, color="grey", alpha=.15); ax.text(1941, s.min()+0.5, "sparse-obs.\nera", fontsize=7)
ax.set_ylabel("Afternoon hours from 270-360° (%)"); ax.set_xlabel("Year"); ax.legend(fontsize=7, loc="lower right")
ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(FIG/"fig4_timeseries.png", dpi=200); plt.close(fig)

# Fig 5: diurnal cycle early vs recent: W-N share and speed
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3.2))
for lab, d, c in [(f"{EARLY[0]}-{EARLY[1]}", h[h.year.between(*EARLY)], "tab:orange"),
                  (f"{RECENT[0]}-{RECENT[1]}", h[h.year.between(*RECENT)], "tab:blue")]:
    a1.plot(range(24), d.groupby("hour").wd.apply(lambda w: in_sector(w, 270, 360).mean()*100), c=c, marker="o", ms=3, label=lab)
    a2.plot(range(24), d.groupby("hour").ws.mean(), c=c, marker="o", ms=3, label=lab)
for a in (a1, a2): a.axvspan(13, 17, color="gold", alpha=.2); a.set_xlabel("Local hour (UTC+3)"); a.set_xticks(range(0, 24, 3)); a.grid(alpha=.3)
a1.set_ylabel("Hours from 270-360° (%)"); a2.set_ylabel("Mean 10 m wind speed (m/s)"); a1.legend(fontsize=7)
fig.tight_layout(); fig.savefig(FIG/"fig5_diurnal.png", dpi=200); plt.close(fig)

# Fig 6: month x hour heatmaps: recent share and recent-minus-early difference
def mh(d): return d.groupby(["month", "hour"]).wd.apply(lambda w: in_sector(w, 270, 360).mean()*100).unstack()
mE, mR = mh(h[h.year.between(*EARLY)]), mh(h[h.year.between(*RECENT)])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.6))
im1 = a1.imshow(mR, aspect="auto", cmap="YlGnBu", vmin=0, vmax=100, origin="lower", extent=[-.5, 23.5, .5, 12.5])
a1.set_title(f"W-N share, {RECENT[0]}-{RECENT[1]} (%)"); fig.colorbar(im1, ax=a1)
dmax = np.nanmax(np.abs((mR-mE).values))
im2 = a2.imshow(mR-mE, aspect="auto", cmap="RdBu", vmin=-dmax, vmax=dmax, origin="lower", extent=[-.5, 23.5, .5, 12.5])
a2.set_title(f"Change vs {EARLY[0]}-{EARLY[1]} (pp)"); fig.colorbar(im2, ax=a2)
for a in (a1, a2):
    a.set_xlabel("Local hour"); a.set_ylabel("Month"); a.set_yticks(range(1, 13)); a.set_xticks(range(0, 24, 3))
fig.tight_layout(); fig.savefig(FIG/"fig6_heatmap.png", dpi=200); plt.close(fig)
(mR-mE).to_csv(TAB/"month_hour_change_pp.csv", float_format="%.2f")
R["mh_change_min"], R["mh_change_max"] = float(np.nanmin((mR-mE).values)), float(np.nanmax((mR-mE).values))
aftchg = (mR-mE).loc[:, 13:17]
R["aft_mh_change_min"], R["aft_mh_change_max"] = float(aftchg.values.min()), float(aftchg.values.max())
(ROOT/"results.json").write_text(json.dumps(R, indent=2, default=float))
print(json.dumps(R, indent=1, default=float)); print(trend_tab.to_string()); print(dec.to_string()); print(sens.to_string())
