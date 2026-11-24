"""Independent check: recomputes key figures from the RAW CSV using only the standard library,
then asserts they match the pandas outputs. Run: python scripts/verify.py
"""
import csv, json, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SEG = {"Talk Football HD": "EU", "Drog BABA": "EU", "Divyansh": "EU", "YjR": "EU",
       "Playmaker India": "IND", "Dhanraj Dhurve": "IND", "Curious Harry": "IND",
       "Football Mania Malayalam": "REG", "Markaroni": "UNC", "Sharma Football": "UNC"}
rows = list(csv.DictReader(open(ROOT / "data/raw/youtube_research_raw.csv", encoding="utf-8")))
analysed, prev = [], None
for r in rows:
    views = r["views_raw"] if r["views_raw"] not in ("N/A", "") else None
    title = r["video_title"] if r["video_title"] not in ("N/A", "") else None
    date = r["publication_date_raw"] if r["publication_date_raw"] not in ("N/A", "") else None
    if prev and prev["creator"] == r["creator"]:
        pv, pd_ = prev["views"], prev["date"]
    else:
        pv, pd_ = None, None
    dup = views is not None and pv == views and (date is None or date == pd_)
    if title and views and not dup:
        analysed.append({"creator": r["creator"], "seg": SEG[r["creator"]], "views": int(views),
                         "live": r["content_format_raw"] and ("live" in r["content_format_raw"].lower() or "stream" in r["content_format_raw"].lower())})
    prev = {"creator": r["creator"], "views": views, "date": date}

checks = {}
for seg in ["EU", "IND", "REG"]:
    checks[f"median_{seg}"] = int(statistics.median([a["views"] for a in analysed if a["seg"] == seg]))
checks["analysis_rows"] = len(analysed)
checks["overall_median"] = int(statistics.median([a["views"] for a in analysed]))
lv = [a["views"] for a in analysed if a["live"]]; nl = [a["views"] for a in analysed if not a["live"]]
checks["livestream_median"] = int(statistics.median(lv)); checks["non_livestream_median"] = int(statistics.median(nl))
checks["divyansh_median"] = int(statistics.median([a["views"] for a in analysed if a["creator"] == "Divyansh"]))

seg_df = {r["segment"]: r for r in csv.DictReader(open(ROOT / "outputs/tables/segment_comparison.csv"))}
key = json.loads((ROOT / "outputs/tables/key_metrics.json").read_text())
expect = {"median_EU": int(seg_df["European football"]["median_views"]),
          "median_IND": int(seg_df["Indian football"]["median_views"]),
          "median_REG": int(seg_df["Regional (Malayalam)"]["median_views"]),
          "analysis_rows": key["analysis_rows"], "overall_median": key["overall_median_views"],
          "livestream_median": key["livestream_median_views"], "non_livestream_median": key["non_livestream_median_views"]}
ok = True
for k, v in expect.items():
    status = "OK " if checks[k] == v else "FAIL"
    ok &= checks[k] == v
    print(f"{status} {k:22s} independent={checks[k]:>8}  pipeline={v:>8}")
print("divyansh_median (independent):", checks["divyansh_median"])
print("ALL CHECKS PASSED" if ok else "MISMATCH FOUND")
raise SystemExit(0 if ok else 1)
