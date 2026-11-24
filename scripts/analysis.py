"""Step 2: analysis tables, key metrics and figures. Run: python scripts/analysis.py"""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PROC, TAB, FIG = ROOT / "data/processed", ROOT / "outputs/tables", ROOT / "outputs/figures"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
COLORS = {"European football": "#1f5fa8", "Indian football": "#e07b00",
          "Regional (Malayalam)": "#2e8b57", "Unclassified": "#999999"}

v = pd.read_csv(PROC / "videos_clean.csv")
c = pd.read_csv(PROC / "creators_clean.csv")
subs = pd.read_csv(PROC / "subscribers_clean.csv")
brands = pd.read_csv(PROC / "monetisation_brands_clean.csv")
a = v[v.in_analysis_set].copy()

# 1. Creator performance with subscribers and views-per-subscriber
cm = a.groupby(["creator", "segment"]).agg(
    videos_analysed=("views", "size"), median_views=("views", "median"),
    mean_views=("views", "mean"), max_views=("views", "max"),
    livestreams=("is_livestream", "sum")).reset_index()
cm["livestream_share_pct"] = (100 * cm.livestreams / cm.videos_analysed).round(1)
recent = a[a.days_before_snapshot.between(0, 14)].groupby("creator").size()
cm["dated_within_14d"] = cm.creator.map(recent).fillna(0).astype(int)
cm["dominant_format"] = cm.creator.map(a.groupby("creator").content_format.agg(lambda s: s.mode().iloc[0]))
cm = cm.merge(subs[["creator", "subscribers_primary", "subscriber_as_of", "subscriber_date_quality", "stale_flag"]], on="creator", how="left")
cm["views_per_subscriber"] = (cm.median_views / cm.subscribers_primary).round(3)
cm[["median_views", "mean_views", "max_views"]] = cm[["median_views", "mean_views", "max_views"]].round(0).astype(int)
cm = cm.sort_values("median_views", ascending=False)
cm.to_csv(TAB / "creator_performance.csv", index=False)

# 2. Segment comparison
seg = a.groupby("segment").agg(creators=("creator", "nunique"), videos=("views", "size"),
    median_views=("views", "median"), mean_views=("views", "mean"), max_views=("views", "max")).reset_index()
seg = seg.merge(cm.groupby("segment").views_per_subscriber.median().rename("median_views_per_subscriber").reset_index(), on="segment", how="left")
seg[["median_views", "mean_views", "max_views"]] = seg[["median_views", "mean_views", "max_views"]].round(0).astype(int)
seg.to_csv(TAB / "segment_comparison.csv", index=False)

# 3. Formats
fmt = a.groupby("content_format").views.agg(videos="size", median_views="median", mean_views="mean").round(0).reset_index()
fmt.to_csv(TAB / "format_summary.csv", index=False)
mix = pd.crosstab(a.segment, a.content_format)
mix.to_csv(TAB / "segment_format_mix.csv")

# 4. Engagement where likes exist (descriptive only)
eng = v[v.likes.notna() & v.views.notna()][["creator", "video_title", "views", "likes"]].copy()
eng["like_rate_pct"] = (100 * eng.likes / eng.views).round(2)
eng.to_csv(TAB / "engagement_where_available.csv", index=False)

# 5. Partnership readiness: evidence fields only
ready = c[["creator", "segment", "subscribers_primary", "subscriber_as_of", "subscriber_date_quality",
           "sponsor_listed", "named_brands", "business_contact", "data_completeness_pct"]].merge(
    cm[["creator", "videos_analysed", "median_views", "views_per_subscriber"]], on="creator", how="left")
ready["videos_analysed"] = ready.videos_analysed.fillna(0).astype(int)
ready["median_views"] = ready.median_views.fillna(0).astype(int)
ready.sort_values("median_views", ascending=False).to_csv(TAB / "partnership_readiness.csv", index=False)

# 6. Key metrics for report builder and verification
top_video = a.loc[a.views.idxmax()]
live = a[a.is_livestream].views
nonlive = a[~a.is_livestream].views
key = {
    "research_rows": int(len(v)), "creators": int(c.shape[0]),
    "analysis_rows": int(len(a)), "titled_rows": int(v.video_title.notna().sum()),
    "subscribers_verified": int(c.subscribers_primary.notna().sum()),
    "subscribers_current_180d": int((subs.subscriber_days_old <= 180).sum()),
    "subscribers_stale_180d": int(subs.stale_flag.sum()),
    "like_rows": int(v.likes.notna().sum()), "comment_rows": int(v.comments.notna().sum()),
    "dated_rows": int(v.pub_date.notna().sum()),
    "overall_median_views": int(a.views.median()), "overall_mean_views": int(round(a.views.mean())),
    "top_video": {"creator": top_video.creator, "title": top_video.video_title, "views": int(top_video.views)},
    "segments": seg.set_index("segment").to_dict("index"),
    "livestream_median_views": int(live.median()), "non_livestream_median_views": int(nonlive.median()),
    "n_livestream": int(len(live)), "n_non_livestream": int(len(nonlive)),
    "sponsor_listed_creators": int(c.sponsor_listed.eq("Yes").sum()),
    "sponsor_none_detected": int(c.sponsor_listed.eq("No sponsors detected").sum()),
    "business_contact_creators": int(c.business_contact.str.startswith("Yes").sum()),
    "mean_completeness_pct": round(float(c.data_completeness_pct.mean()), 1),
    "views_per_sub_creators": int(cm.views_per_subscriber.notna().sum()),
    "views_per_sub_min": float(cm.views_per_subscriber.min()), "views_per_sub_max": float(cm.views_per_subscriber.max()),
    "divyansh_views_per_sub": float(cm.set_index("creator").loc["Divyansh", "views_per_subscriber"]),
}
(TAB / "key_metrics.json").write_text(json.dumps(key, indent=2, default=str))

# Figures
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
f = cm.sort_values("median_views")
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(f.creator, f.median_views, color=[COLORS[s] for s in f.segment])
for y, (mv, n) in enumerate(zip(f.median_views, f.videos_analysed)):
    ax.text(mv, y, f"  {mv:,} (n={n})", va="center", fontsize=8)
ax.set_xlabel("Median views per analysed video"); ax.set_xlim(0, f.median_views.max() * 1.35)
ax.set_title("Fig 1. Median views by creator (snapshot Nov 2026)", loc="left")
handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[s]) for s in COLORS]
ax.legend(handles, COLORS.keys(), frameon=False, fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "fig1_median_views_by_creator.png", dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.5))
order = [s for s in COLORS if s in a.segment.unique()]
for i, s in enumerate(order):
    vals = a[a.segment == s].views
    x = [i + (j - len(vals) / 2) * 0.04 for j in range(len(vals))]
    ax.scatter(x, vals, color=COLORS[s], alpha=0.8, s=35)
    ax.hlines(vals.median(), i - 0.25, i + 0.25, color="black", lw=2)
ax.set_xticks(range(len(order))); ax.set_xticklabels([f"{s}\n(n={int((a.segment==s).sum())})" for s in order])
ax.set_yscale("log"); ax.set_ylabel("Views per video (log scale)")
ax.set_title("Fig 2. Views per video by segment (black line = median)", loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig2_views_by_segment.png", dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.5))
bottom = pd.Series(0, index=mix.index)
palette = plt.cm.Set2.colors
for i, col in enumerate(mix.columns):
    ax.bar(mix.index, mix[col], bottom=bottom, label=col, color=palette[i % len(palette)])
    bottom += mix[col]
ax.set_ylabel("Number of analysed videos"); ax.legend(frameon=False, fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
ax.set_title("Fig 3. Content format mix by segment", loc="left")
plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
fig.tight_layout(); fig.savefig(FIG / "fig3_format_mix_by_segment.png", dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.5, 4.8))
s4 = cm[cm.subscribers_primary.notna()]
for _, r in s4.iterrows():
    ax.scatter(r.subscribers_primary, r.median_views, color=COLORS[r.segment], s=60)
    yr = str(r.subscriber_as_of)[:4] if pd.notna(r.subscriber_as_of) else "undated"
    ax.annotate(f"{r.creator} ({yr})", (r.subscribers_primary, r.median_views), fontsize=8, xytext=(5, 3), textcoords="offset points")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Subscribers (latest dated tracker value)"); ax.set_ylabel("Median views per analysed video")
ax.set_title("Fig 4. Median views vs subscribers (year in brackets = subscriber date)", loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig4_views_vs_subscribers.png", dpi=150); plt.close(fig)

print(cm[["creator", "videos_analysed", "median_views", "subscribers_primary", "subscriber_as_of", "views_per_subscriber"]].to_string(index=False))
print(seg.to_string(index=False))
print(json.dumps({k: key[k] for k in ["subscribers_verified", "subscribers_current_180d", "sponsor_listed_creators",
                                       "business_contact_creators", "views_per_sub_min", "views_per_sub_max",
                                       "divyansh_views_per_sub", "livestream_median_views", "non_livestream_median_views"]}, indent=1))
