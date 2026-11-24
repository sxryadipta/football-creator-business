"""Step 3: build the business analysis report and the hypothetical partnership proposal (PDF).
Run: python scripts/build_reports.py   (after clean.py and analysis.py). All numbers come from outputs/ and data/processed/.
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

ROOT = Path(__file__).resolve().parents[1]
T, F, P, R = ROOT / "outputs/tables", ROOT / "outputs/figures", ROOT / "data/processed", ROOT / "reports"
R.mkdir(parents=True, exist_ok=True)
K = json.loads((T / "key_metrics.json").read_text())
perf = pd.read_csv(T / "creator_performance.csv")
seg = pd.read_csv(T / "segment_comparison.csv").set_index("segment")
fmt = pd.read_csv(T / "format_summary.csv").set_index("content_format")
ready = pd.read_csv(T / "partnership_readiness.csv")
subs = pd.read_csv(P / "subscribers_clean.csv")
dq = pd.read_csv(P / "data_quality_log.csv")
brands = pd.read_csv(P / "monetisation_brands_clean.csv")
videos = pd.read_csv(P / "videos_clean.csv")

ss = getSampleStyleSheet()
NAVY = colors.HexColor("#1f2d3d"); BLUE = colors.HexColor("#1f5fa8")
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, spaceAfter=6, textColor=NAVY)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4, textColor=BLUE)
BODY = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.5, leading=13.5, spaceAfter=6)
SMALL = ParagraphStyle("S", parent=BODY, fontSize=7.8, leading=9.6, spaceAfter=0)
CAP = ParagraphStyle("C", parent=BODY, fontSize=8, leading=10, textColor=colors.HexColor("#555555"))


def p(text, style=BODY):
    return Paragraph(text, style)


def table(df, widths=None):
    rows = [[Paragraph(f"<b>{escape(str(c))}</b>", SMALL) for c in df.columns]]
    for r in df.itertuples(index=False):
        rows.append([Paragraph(escape(str(x)), SMALL) for x in r])
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b8c4d0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def figure(name, caption, width=16 * cm):
    path = F / name
    iw, ih = ImageReader(str(path)).getSize()
    return [Image(str(path), width=width, height=width * ih / iw), p(caption, CAP), Spacer(1, 6)]


def build(path, story, title, short):
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.grey)
        canvas.drawString(2 * cm, 1.2 * cm, short)
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm, title=title, author="Project analysis")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


# ---------- numbers used in narrative ----------
eu, ind, reg = seg.loc["European football"], seg.loc["Indian football"], seg.loc["Regional (Malayalam)"]
com, mrev = fmt.loc["Commentary / news"], fmt.loc["Match review / preview"]
pc = perf.set_index("creator")
rd = ready.set_index("creator")
div_subs = int(rd.loc["Divyansh", "subscribers_primary"])
div_ratio = K["divyansh_views_per_sub"]
named = brands[brands.brand != "None detected"]
verified_n = K["subscribers_verified"]
unverified = subs[subs.subscribers_primary.isna()].creator.tolist()
live_n, nonlive_n = K["n_livestream"], K["n_non_livestream"]
n_stale = K["subscribers_stale_180d"]

# =====================================================================
# REPORT
# =====================================================================
s = []
s.append(p("Business Analysis of the Indian Football Creator Ecosystem", H1))
s.append(p("Snapshot dated 24 November 2026 · 10 channels · 32 research rows · Descriptive analysis (verified update)", CAP))
s.append(Spacer(1, 8))

s.append(p("1. Executive summary", H2))
s.append(p(
    f"This update verifies subscriber counts and sponsorship records for the {K['creators']} channels in the sample. "
    f"Subscriber counts are now available for {verified_n} of {K['creators']} creators, up from none. Only one of them is current: "
    f"Divyansh at {div_subs:,} (NexLev, 14 November 2026). The other {verified_n - 1} figures date from 2025 or are undated live counters, so "
    f"{n_stale} of the values are more than 180 days old and should be treated as indicative. {len(unverified)} creators "
    f"({', '.join(unverified)}) could not be verified and are left blank rather than estimated."))
s.append(p(
    f"Reach is concentrated in European-focused channels. Their pooled median is {eu.median_views:,.0f} views per analysed video (n={int(eu.videos)}), against "
    f"{ind.median_views:,.0f} for Indian-focused channels (n={int(ind.videos)}) and {reg.median_views:,.0f} for the single Malayalam-language channel (n={int(reg.videos)}). "
    f"Among channels with both figures, median views per subscriber range from {K['views_per_sub_min']:.2f} to {K['views_per_sub_max']:.2f}. "
    f"The highest ratio belongs to YjR, but its subscriber figure is from May 2025, so the true ratio is probably lower."))
s.append(p(
    "<b>Correction to the first version.</b> The earlier report said sponsorship evidence existed for only two creators and that it did not track reach. "
    f"Verification shows sponsorship is listed for {K['sponsor_listed_creators']} creators, including YjR, the channel with the highest median views, and Divyansh. "
    "The original research missed these listings. Sponsorship is therefore common among high-reach European channels, which makes them more competitive for "
    "a new brand rather than under-monetised."))

s.append(p("2. Data, verification and method", H2))
s.append(p(
    f"The research was transcribed into structured CSVs ({K['research_rows']} rows, {K['titled_rows']} with titles, {K['dated_rows']} with dates, "
    f"{K['like_rows']} with likes, {K['comment_rows']} with comments). Subscriber counts and sponsor listings were checked against public sources "
    "(vidIQ, NexLev, SponsorRadar, SocialCounts, Tring, Modash, and TEDx and press bios). Every observation, with its source, URL and as-of date, is in "
    "<i>subscriber_observations_clean.csv</i>. The primary subscriber figure is the latest dated tracker value. Where no dated value exists, the undated "
    "live counter is used and flagged. Modash entries are excluded from the primary figure because several cards are mislabelled. "
    "Video-level likes, comments and dates could not be verified: the watch pages were blocked during checking, so those values remain N/A and nothing was estimated. "
    "Segments are analyst-assigned from title content, and formats are normalised by keyword rules."))

s.append(p("3. Creator performance", H2))
s.append(p(
    f"Medians are the most robust summary here because single viral videos pull means upward. YjR has the highest median ({pc.loc['YjR','median_views']:,}) "
    f"and peak views ({K['top_video']['views']:,} on \"{escape(K['top_video']['title'])}\"), but that median rests on four videos. "
    f"Playmaker India has the most analysed videos (n={pc.loc['Playmaker India','videos_analysed']}) and a median of "
    f"{pc.loc['Playmaker India','median_views']:,}, yet no subscriber figure could be verified for it."))
t1 = perf[["creator", "videos_analysed", "median_views", "subscribers_primary", "subscriber_as_of", "views_per_subscriber", "dominant_format"]].copy()
t1["subscribers_primary"] = t1.subscribers_primary.map(lambda x: f"{int(x):,}" if pd.notna(x) else "Not verified")
t1["subscriber_as_of"] = t1.subscriber_as_of.fillna("undated / n.a.")
t1["views_per_subscriber"] = t1.views_per_subscriber.map(lambda x: f"{x:.2f}" if pd.notna(x) else "n.a.")
t1.columns = ["Creator", "Videos", "Median views", "Subscribers", "As of", "Views per sub.", "Dominant format"]
s.append(table(t1, widths=[3.3 * cm, 1.2 * cm, 2.0 * cm, 2.2 * cm, 2.3 * cm, 2.0 * cm, 4.0 * cm]))
s.append(Spacer(1, 8))
s += figure("fig1_median_views_by_creator.png", "Figure 1. Median views per analysed video by creator. n = analysed videos per channel.")

s.append(p("4. European, Indian and regional comparison", H2))
s.append(p(
    f"European-focused channels: four channels, {int(eu.videos)} videos, median {eu.median_views:,.0f}, maximum {eu.max_views:,}. "
    f"Indian-focused channels: three channels, {int(ind.videos)} videos, median {ind.median_views:,.0f}, maximum {ind.max_views:,}. "
    f"The regional segment has one creator and three videos, so no conclusion about regional creators is supported beyond the low reach observed on that channel. "
    f"The European and Indian gap holds at the level of individual channels, not only at the pooled level."))
s += figure("fig2_views_by_segment.png", "Figure 2. Views per analysed video by segment (log scale). Black line marks the segment median.")

s.append(p("5. Views relative to subscribers", H2))
s.append(p(
    f"Views per subscriber is the median video's views divided by the channel's latest dated subscriber count. It is a rough reach ratio, not an engagement rate, "
    f"and the subscriber figures come from different dates. For the four European channels with a verified count, the median ratio is "
    f"{seg.loc['European football','median_views_per_subscriber']:.2f}. "
    f"The Indian ratio ({seg.loc['Indian football','median_views_per_subscriber']:.2f}) rests on one creator, Dhanraj Dhurve, with an undated count, so it should not be compared directly. "
    f"Divyansh's ratio of {div_ratio:.2f} is calculated from a current count and three videos."))
s += figure("fig4_views_vs_subscribers.png", "Figure 3. Median views against subscribers. Channels without a verified count are omitted.", width=14 * cm)

s.append(p("6. Content formats", H2))
s.append(p(
    f"Commentary and news content has a median of {com.median_views:,.0f} views across {com.videos} videos. Match review and preview content has a median of "
    f"{mrev.median_views:,.0f} across {mrev.videos}. Livestreams have a median of {K['livestream_median_views']:,} (n={live_n}), against "
    f"{K['non_livestream_median_views']:,} for other formats (n={nonlive_n}). These are small samples, so treat them as directional. "
    f"Playmaker India posted {int(pc.loc['Playmaker India','dated_within_14d'])} dated videos in the 14 days before the snapshot, but its reach per video is lower."))
s += figure("fig3_format_mix_by_segment.png", "Figure 4. Analysed videos by normalised content format and segment.", width=15 * cm)

s.append(p("7. Monetisation: sponsorship, membership and merchandise", H2))
s.append(p(
    f"SponsorRadar lists sponsors for Talk Football HD, Divyansh, and YjR. Its listings are estimates deduced from video content, not confirmed by the channels or brands. "
    f"For Divyansh and YjR, SponsorRadar reports nine brands each; the table names the ones with video counts or named partners. "
    f"Drog BABA shows no sponsors detected. Markaroni's FanCode listing comes from the original research and was not re-verified. "
    "Membership and merchandise evidence is absent for all creators, so those revenue lines cannot be assessed. No revenue, rate or CPM data is available."))
m_show = brands[["creator", "brand", "sponsored_videos", "verification"]].copy()
m_show["sponsored_videos"] = m_show.sponsored_videos.map(lambda x: f"{int(x)}" if pd.notna(x) else "Not shown")
m_show.columns = ["Creator", "Brand", "Sponsored videos", "Verification"]
s.append(table(m_show, widths=[3.6 * cm, 3.6 * cm, 2.8 * cm, 7.0 * cm]))
s.append(Spacer(1, 6))

s.append(p("8. Insights, segments and business opportunities", H2))
s.append(p(
    "<b>Segment A: high-reach European commentary.</b> YjR, Drog BABA, Divyansh and Talk Football HD combine the highest observed reach with topical commentary. "
    "All four have listed sponsors or no sponsors detected, so the commercial market is active. A new brand has to differentiate on audience fit, not on access."))
s.append(p(
    "<b>Segment B: Indian national-team content.</b> These channels publish frequently around tournaments. Reach per video is lower, and the subscriber figure for "
    "Playmaker India, the largest of them by video count, is unverified. Tournament packages across a series are a reasonable hypothesis, but this segment "
    "cannot be sized until subscriber data is collected."))
s.append(p(
    "<b>Segment C: regional and niche.</b> The Malayalam-language channel has low absolute views and no verified subscriber count. Its high like rates on two "
    "tribute videos are a hypothesis for follow-up, not a finding."))
s.append(p(
    "<b>Opportunities.</b> (1) Sponsorship packages for high-reach European channels where audience fit can be proven with current analytics. "
    "(2) Tournament-linked packages for Indian national-team content, once subscriber and view data is verified for the main channels. "
    "(3) Livestream integrations, which show higher median views in the sample but need testing. "
    "(4) Membership and merchandise models cannot be recommended from this dataset."))

s.append(p("9. Limitations and data corrections", H2))
s.append(p(
    f"Average completeness across seven key fields is {K['mean_completeness_pct']}%. Four creators have no verified subscriber count, and the rest mostly date from 2025. "
    "The table below records every limitation and every correction made in this update."))
dq_show = dq[["issue", "scope", "handling"]].copy()
dq_show.columns = ["Issue", "Scope", "Handling"]
s.append(table(dq_show, widths=[5.6 * cm, 4.0 * cm, 7.4 * cm]))
s.append(Spacer(1, 6))
s.append(p(
    "Recommended next steps: obtain current subscriber counts and 90-day analytics for the four unverified creators, verify the video-level values from the "
    "watch pages, confirm the Markaroni sponsor listing, and extend the sample to at least 10 videos per channel before drawing segment conclusions."))

build(R / "business_analysis_report.pdf", s, "Business Analysis of the Indian Football Creator Ecosystem",
      "Business Analysis · Indian Football Creator Ecosystem · verified update")

# =====================================================================
# PROPOSAL (hypothetical)
# =====================================================================
q = []
q.append(p("Hypothetical Brand Partnership Proposal", H1))
q.append(p("Creator: Divyansh (YouTube, @DivyanshCR7) · Brand: [Hypothetical Brand], a fictional sports-apparel label · Status: DRAFT, not sent", CAP))
q.append(Spacer(1, 8))
q.append(p("1. Why this creator", H2))
q.append(p(
    f"Divyansh is the only creator in the sample with a current, verified subscriber count ({div_subs:,}, NexLev, 14 November 2026). "
    f"The median of the {int(rd.loc['Divyansh','videos_analysed'])} analysed videos is {int(rd.loc['Divyansh','median_views']):,} views, with a peak of "
    f"{int(pc.loc['Divyansh','max_views']):,}. That gives a views-per-subscriber ratio of {div_ratio:.2f}, which sits in the middle of the verified range. "
    "The channel's About page lists a business enquiry contact, so first outreach is straightforward."))
q.append(p(
    "Divyansh already works with brands. SponsorRadar lists nine brands, with Blank the most frequent (11 videos), and names Streamyard and Fancode among others. "
    "Experience of sponsorship lowers execution risk. It also means the brand must check for category conflicts with those existing partners before any approach."))
q.append(p(
    "Why not the other channels: YjR has the highest median (137,000) but its subscriber count is from May 2025, so its ratio cannot be trusted. "
    "Talk Football HD and Drog BABA have older counts too. Playmaker India, the most active Indian channel, has no verified count. "
    "The choice is conditional on the verification steps in section 7."))
q.append(p("2. Proposed collaboration", H2))
q.append(p(
    "A single integrated campaign with three components, sized to the formats the creator has published in the sample: "
    "(a) one dedicated video of 8 to 12 minutes with a clearly labelled brand segment placed early; "
    "(b) one livestream watchalong segment of 15 to 20 minutes featuring the brand, timed to a match day; and "
    "(c) one community post linking to the campaign landing page. Creative control stays with the creator, subject to a brand-safety review of the script."))
q.append(p("3. Reach planning benchmarks (from the research, not guaranteed)", H2))
planning = pd.DataFrame([
    ["Integrated video", "39,000 to 241,000", f"Median {int(rd.loc['Divyansh','median_views']):,} across the analysed videos"],
    ["Livestream", "62,000 to 78,000 (sample)", "Ballon d'Or stream 78,000; Drog BABA GTA VI stream 62,000 as the closest comparable in the sample"]],
    columns=["Component", "Observed view range", "Basis"])
q.append(table(planning, widths=[3.4 * cm, 4.5 * cm, 8.7 * cm]))
q.append(Spacer(1, 4))
q.append(p(
    "These ranges are planning guides, not commitments. The creator should supply 90-day analytics before any reach commitment is written into a contract, "
    "because a three-video median is a thin basis for a guarantee."))
q.append(p("4. Commercial terms", H2))
q.append(p(
    "Fee: [to be negotiated]. The research contains no rate card, CPM or revenue data for this creator, so no fee is proposed. "
    "Any performance bonus should be agreed against verified analytics. Usage rights for repurposing clips are to be defined in the contract."))
q.append(p("5. Measurement", H2))
q.append(p(
    "Primary KPIs: views and watch time on campaign content, UTM-tagged link clicks, and promo-code redemptions if a code is issued. "
    "Targets should be set after the creator's analytics are reviewed."))
q.append(p("6. Brand safety, disclosure and conflicts", H2))
q.append(p(
    "All sponsored content must carry the platform's paid-promotion disclosure and an on-screen sponsored label. Before signing, the brand should confirm that "
    "no competing category partner is active on the channel (SponsorRadar names Streamyard and Fancode) and should review commentary on club rivalries and player conduct."))
q.append(p("7. Next steps", H2))
q.append(p(
    "(1) Confirm the channel's current subscriber count, 90-day analytics and audience location. (2) Check its current sponsor list directly with the creator. "
    "(3) Send first contact through the business enquiry address on the channel's About page. (4) Agree fee, deliverables and KPIs in a short term sheet. "
    "(5) Hold a brand-safety and conflicts review before filming."))
q.append(Spacer(1, 6))
q.append(p(
    "<i>This is a hypothetical proposal produced for a portfolio project. The brand is fictional. Creator figures come from public sources as of the dates shown, "
    "and have not been verified by the creator. No offer has been made to Divyansh.</i>", CAP))
build(R / "brand_partnership_proposal.pdf", q, "Hypothetical Brand Partnership Proposal",
      "Hypothetical proposal · Divyansh · Draft")
print("Reports written:", sorted(x.name for x in R.glob("*.pdf")))
