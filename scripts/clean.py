"""Step 1: clean raw research into structured CSVs. Run: python scripts/clean.py"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data/raw", ROOT / "data/processed"
PROC.mkdir(parents=True, exist_ok=True)
SNAPSHOT = pd.Timestamp("2026-11-24")
STALE_DAYS = 180
NA = ["N/A", "n/a", ""]

# Analyst-assigned segments, based only on the content focus of listed titles.
SEGMENTS = {
    "Talk Football HD": ("European football", "Titles focus on European clubs"),
    "Drog BABA": ("European football", "Titles focus on Man United / Real Madrid / gaming"),
    "Divyansh": ("European football", "Titles focus on Real Madrid / Ballon d'Or"),
    "YjR": ("European football", "Titles focus on Barcelona / Man United / Portugal"),
    "Playmaker India": ("Indian football", "Titles focus on India national and youth teams"),
    "Dhanraj Dhurve": ("Indian football", "Titles focus on India squads and FIFA U15"),
    "Curious Harry": ("Indian football", "Titles focus on Indian football"),
    "Football Mania Malayalam": ("Regional (Malayalam)", "Malayalam-language titles; Kerala club matchday content"),
    "Markaroni": ("Unclassified", "No content evidence in dataset"),
    "Sharma Football": ("Unclassified", "No content evidence in dataset"),
}
BUSINESS_CONTACT = {
    "Divyansh": "Yes (NexLev; SponsorRadar; channel About page)",
}
KEY_FIELDS = ["video_title", "video_url", "publication_date_raw", "views_raw",
              "likes_raw", "comments_raw", "content_format_raw"]


def norm_format(s):
    """Map free-text format labels to a fixed taxonomy (keyword rules, order matters)."""
    if pd.isna(s):
        return "Unspecified"
    s = str(s).lower()
    rules = [("live", "Live / Watchalong"), ("stream", "Live / Watchalong"),
             ("match review", "Match review / preview"), ("preview", "Match review / preview"),
             ("match reaction", "Match reaction"), ("explainer", "Explainer"),
             ("tribute", "Tribute / motivation"), ("motivation", "Tribute / motivation"),
             ("vlog", "Vlog"), ("commentary", "Commentary / news"), ("news", "Commentary / news"),
             ("analysis", "Commentary / news"), ("reaction", "Commentary / news"),
             ("special", "Commentary / news")]
    for key, label in rules:
        if key in s:
            return label
    return "Unspecified"


def clean_videos():
    v = pd.read_csv(RAW / "youtube_research_raw.csv", na_values=NA, keep_default_na=False)
    v["views"] = pd.to_numeric(v.views_raw, errors="coerce")
    v["likes"] = pd.to_numeric(v.likes_raw, errors="coerce")
    v["comments"] = pd.to_numeric(v.comments_raw, errors="coerce")
    v["pub_date"] = pd.to_datetime(v.publication_date_raw, errors="coerce")
    v["days_before_snapshot"] = (SNAPSHOT - v.pub_date).dt.days
    v["segment"] = v.creator.map(lambda c: SEGMENTS[c][0])
    v["content_format"] = v.content_format_raw.map(norm_format)
    v["is_livestream"] = v.content_format.eq("Live / Watchalong")
    v["has_title"] = v.video_title.notna()
    prev_views = v.groupby("creator").views.shift()
    prev_date = v.groupby("creator").pub_date.shift()
    # Possible copy error: same views as previous row AND (date missing or same date as previous row)
    v["flag_views_equal_prev"] = (prev_views == v.views) & v.views.notna() & (v.pub_date.isna() | (v.pub_date == prev_date))
    v["flag_non_video_url"] = v.video_url.str.contains(r"/about|don123xxxx", regex=True, na=False)
    v["flag_missing_date"] = v.pub_date.isna()
    v["flag_missing_views"] = v.views.isna()
    v["in_analysis_set"] = v.has_title & v.views.notna() & ~v.flag_views_equal_prev
    v["pub_date"] = v.pub_date.dt.strftime("%Y-%m-%d")
    cols = ["creator", "segment", "video_title", "video_url", "pub_date", "days_before_snapshot",
            "views", "likes", "comments", "content_format", "is_livestream", "in_analysis_set",
            "flag_views_equal_prev", "flag_non_video_url", "flag_missing_date", "flag_missing_views", "date_note"]
    v[cols].to_csv(PROC / "videos_clean.csv", index=False)
    return v


def clean_subscribers():
    obs = pd.read_csv(RAW / "subscriber_observations_raw.csv", na_values=NA, keep_default_na=False)
    obs["subscribers"] = pd.to_numeric(obs.subscribers_raw, errors="coerce")
    obs["as_of"] = pd.to_datetime(obs.as_of_raw, errors="coerce")
    obs["days_old"] = (SNAPSHOT - obs.as_of).dt.days
    obs["use_for_primary"] = obs.use_for_primary.str.upper().eq("Y")
    obs["as_of"] = obs.as_of.dt.strftime("%Y-%m-%d")
    obs[["creator", "subscribers", "as_of", "days_old", "source", "source_url", "use_for_primary", "notes"]] \
        .to_csv(PROC / "subscriber_observations_clean.csv", index=False)

    rows = []
    for name in SEGMENTS:
        g = obs[(obs.creator == name)]
        use = g[g.use_for_primary]
        row = {"creator": name, "n_observations": len(g),
               "subscribers_min_observed": g.subscribers.min() if len(g) else None,
               "subscribers_max_observed": g.subscribers.max() if len(g) else None}
        if len(use):
            # Primary = latest dated tracker value; undated values only used if no dated value exists.
            top = use.assign(_d=use.as_of.notna()).sort_values(["_d", "as_of"], ascending=[False, False]).iloc[0]
            row.update({"subscribers_primary": top.subscribers, "subscriber_as_of": top.as_of,
                        "primary_source": top.source,
                        "subscriber_date_quality": "dated" if pd.notna(top.as_of) else "undated live counter",
                        "subscriber_days_old": top.days_old})
        else:
            row.update({"subscribers_primary": None, "subscriber_as_of": None, "primary_source": "Not verified",
                        "subscriber_date_quality": "not verified", "subscriber_days_old": None})
        row["stale_flag"] = bool(pd.notna(row["subscriber_days_old"]) and row["subscriber_days_old"] > STALE_DAYS)
        rows.append(row)
    subs = pd.DataFrame(rows)
    subs.to_csv(PROC / "subscribers_clean.csv", index=False)
    return subs


def clean_brands():
    b = pd.read_csv(RAW / "monetisation_brands_raw.csv", na_values=NA, keep_default_na=False)
    b["segment"] = b.creator.map(lambda c: SEGMENTS[c][0])
    b["sponsored_videos"] = pd.to_numeric(b.sponsored_videos_raw, errors="coerce")
    b.drop(columns=["sponsored_videos_raw"]).to_csv(PROC / "monetisation_brands_clean.csv", index=False)
    return b


def main():
    v = clean_videos()
    subs = clean_subscribers()
    b = clean_brands()
    rows = []
    for name, (seg, basis) in SEGMENTS.items():
        sub = v[v.creator == name]
        br = b[b.creator == name]
        named = br[br.brand != "None detected"]
        if br.brand.eq("None detected").any():
            sponsor = "No sponsors detected"
        elif len(named):
            sponsor = "Yes"
        else:
            sponsor = "Not verified"
        s = subs[subs.creator == name].iloc[0]
        rows.append({
            "creator": name, "segment": seg, "segment_basis": basis,
            "research_rows": len(sub), "titled_rows": int(sub.has_title.sum()),
            "rows_with_views": int(sub.views.notna().sum()),
            "rows_with_dates": int(sub.pub_date.notna().sum()),
            "rows_with_likes": int(sub.likes.notna().sum()),
            "data_completeness_pct": round(100 * sub[KEY_FIELDS].notna().values.mean(), 1),
            "subscribers_primary": s.subscribers_primary,
            "subscriber_as_of": s.subscriber_as_of,
            "subscriber_date_quality": s.subscriber_date_quality,
            "sponsor_listed": sponsor,
            "named_brands": len(named),
            "business_contact": BUSINESS_CONTACT.get(name, "Not verified"),
        })
    pd.DataFrame(rows).to_csv(PROC / "creators_clean.csv", index=False)

    v_missing = int(v.likes.isna().sum())
    n = len(v)
    dq = [
        ("Subscriber counts verified (dated or live counter)", f"{int(subs.subscribers_primary.notna().sum())} of {len(SEGMENTS)} creators",
         "Used for views-per-subscriber; missing creators excluded from that metric"),
        ("Subscriber counts older than 180 days at snapshot", f"{int(subs.stale_flag.sum())} creators",
         "Shown with as-of date; ratios for these are indicative only"),
        ("Subscriber counts undated (live counter)", f"{int((subs.subscriber_date_quality=='undated live counter').sum())} creator",
         "Used only because no dated tracker value was found; flagged"),
        ("Subscriber source disagreement", "Talk Football HD, Markaroni, Drog BABA, Divyansh, YjR, Dhanraj Dhurve",
         "Primary = latest dated tracker value; full range kept in subscriber_observations_clean.csv"),
        ("Subscriber counts not found", "Playmaker India, Football Mania Malayalam, Curious Harry, Sharma Football",
         "Left as not verified; no value estimated"),
        ("Like counts missing", f"{v_missing} of {n} rows", "Watch pages could not be fetched (rate limit / consent page); left N/A"),
        ("Comment counts missing", f"{int(v.comments.isna().sum())} of {n} rows", "As above; not analysed"),
        ("Publication date missing", f"{int(v.flag_missing_date.sum())} rows", "Excluded from date/recency metrics only; not filled"),
        ("View count missing", f"{int(v.flag_missing_views.sum())} rows", "Excluded from view metrics; not filled"),
        ("Duplicate view count on consecutive rows (possible copy error)", f"{int(v.flag_views_equal_prev.sum())} row(s)", "Excluded from analysis set; flagged"),
        ("Non-video or unverifiable URL pattern (/about page, don123xxxx)", f"{int(v.flag_non_video_url.sum())} rows", "Kept in analysis; flagged for manual verification"),
        ("Relative-age text anchored to different dates", f"{int(v.date_note.fillna('').str.contains('reported|streamed').sum())} rows", "Relative ages ignored; absolute dates used only"),
        ("Creators with no video-level data", "Markaroni, Sharma Football", "Profile only; excluded from performance metrics"),
        ("Playmaker India videos all point to one channel page", f"{int(v.video_url.str.contains('playmakerindia', na=False).sum())} rows", "Individual video URLs cannot be verified"),
        ("Sponsor correction: Talk Football HD", "1 creator", "Original research named Deadbeat top sponsor (48 videos); SponsorRadar lists Vezer and Deadbeat at 93 each"),
        ("Sponsor correction: Divyansh and YjR", "2 creators", "Original research recorded no sponsor evidence; SponsorRadar lists 9 brands for each"),
        ("Sponsor not re-verified: Markaroni (FanCode)", "1 creator", "Carried over from original research; not checked this session"),
        ("Modash list entries inconsistent with other sources", "Markaroni, Drog BABA, Dhanraj Dhurve", "Excluded from primary; kept as low-confidence observations"),
        ("Segment labels analyst-assigned from titles", f"{len(SEGMENTS)} creators", "Documented assumption; not a verified attribute"),
        ("Non-random sample from search snippets", "Whole dataset", "Results describe this snapshot only"),
    ]
    pd.DataFrame(dq, columns=["issue", "scope", "handling"]).to_csv(PROC / "data_quality_log.csv", index=False)
    print(f"Cleaned {n} video rows, {len(subs)} creators, {len(subs)} subscriber primaries; analysis set {int(v.in_analysis_set.sum())} rows")


if __name__ == "__main__":
    main()
