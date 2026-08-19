from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="SafeReturn Local",
    page_icon="🛟",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA = Path("data/synthetic_sighting_registry.csv")
REQ = ['case_id', 'case_code', 'age_band', 'last_known_zone', 'last_known_time', 'sighting_id', 'sighting_zone', 'sighting_time', 'source_type', 'source_verified', 'confidence_score', 'direction_consistency_score', 'time_consistency_score', 'location_consistency_score', 'safe_reporting_channel', 'duplicate_check', 'search_zone_priority', 'responder_review_status']

st.markdown("""
<style>
.stApp{background:#f5f8f7;color:#17221d}
.block-container{max-width:1500px;padding:1.25rem 2rem 3rem}
[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid #dfe8e3}
[data-testid="stSidebar"] *{color:#26342d!important}
.hero{background:linear-gradient(135deg,#ffffff 0%,#edf7f2 100%);
border:1px solid #dbe8e1;border-radius:28px;padding:30px 34px;margin-bottom:18px;
box-shadow:0 12px 35px rgba(25,55,40,.07)}
.hero h1{font-size:2.55rem;color:#14221a;margin:14px 0 8px;letter-spacing:-.035em}
.hero p{color:#58665f;line-height:1.65}
.pill{display:inline-block;padding:7px 12px;margin-right:6px;border-radius:999px;
background:#edf7f1;border:1px solid #d2e7da;color:#27613f;font-size:.72rem;font-weight:800}
.card{background:#fff;border:1px solid #dfe8e3;border-radius:20px;padding:20px;margin:12px 0}
.small{color:#65736c;font-size:.9rem}
.warning{background:#fff8e8;border:1px solid #ead9a8;border-radius:16px;padding:15px;color:#66521e}
</style>
""", unsafe_allow_html=True)

def num(v):
    try:
        return float(v)
    except:
        return 0.0

def verified(v):
    return str(v).strip().lower() in {"yes","true","1","verified","current"}

def calc_score(r):
    base = np.mean([
        num(r.confidence_score),
        num(r.direction_consistency_score),
        num(r.time_consistency_score),
        num(r.location_consistency_score)
    ])
    penalty = 0
    notes = []

    if not verified(r.source_verified):
        penalty += 25
        notes.append("Source has not been verified; do not treat the sighting as actionable.")
    if not verified(r.safe_reporting_channel):
        penalty += 12
        notes.append("Safe reporting channel is not confirmed.")
    if "duplicate" in str(r.duplicate_check).lower():
        penalty += 18
        notes.append("Possible duplicate report requires human verification.")
    if num(r.confidence_score) < 60:
        penalty += 12
        notes.append("Confidence signal is low.")
    if num(r.location_consistency_score) < 60:
        penalty += 10
        notes.append("Location consistency signal is low.")

    score = float(np.clip(base - penalty, 0, 100))

    if not verified(r.source_verified):
        band = "VERIFY FIRST"
    elif score >= 85:
        band = "HIGH REVIEW"
    elif score >= 65:
        band = "MODERATE REVIEW"
    else:
        band = "LOW CONFIDENCE"

    return score, band, notes

try:
    df = pd.read_csv(DATA)
    missing = [c for c in REQ if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    scored = df.apply(calc_score, axis=1, result_type="expand")
    scored.columns = ["verification_score", "review_band", "factor_notes"]
    df = pd.concat([df.reset_index(drop=True), scored], axis=1)
except Exception as e:
    df = pd.DataFrame(columns=REQ)
    st.error(str(e))

st.sidebar.markdown("## 🛟 SafeReturn Local")
st.sidebar.caption("Missing-child safe-return coordination support")
page = st.sidebar.radio(
    "Workspace",
    ["Coordination Center","Sighting Review","Search-Zone Matrix","Verification Queue","Local Data Lab","Privacy & Safety"]
)
st.sidebar.markdown("---")
st.sidebar.caption("100% local • No external APIs")

st.markdown("""
<div class="hero">
<span class="pill">LOCAL-FIRST</span>
<span class="pill">PRIVACY-FIRST</span>
<span class="pill">VERIFICATION-FIRST</span>
<span class="pill">HUMAN REVIEW</span>
<h1>🛟 SafeReturn Local</h1>
<p><b>Missing Child Safe-Return Coordinator</b> — organize verified or pending sightings, last-known details, safe reporting signals, and coarse search-zone prioritization for authorized responders.</p>
<p><b>Critical safety boundary:</b> This is operational decision support only. It does not replace police, emergency services, child-protection professionals, or established missing-child procedures. Do not use it for public identification, independent surveillance, confrontation, or sharing sensitive location information.</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.info("Load a valid authorized/synthetic sighting registry in Local Data Lab.")
elif page == "Coordination Center":
    a,b,c,d,e = st.columns(5)
    a.metric("Reports", len(df))
    b.metric("Verified", int(df.source_verified.apply(verified).sum()))
    c.metric("Needs verification", int((~df.source_verified.apply(verified)).sum()))
    d.metric("High-review signals", int((df.verification_score >= 85).sum()))
    e.metric("Possible duplicates", int(df.duplicate_check.astype(str).str.contains("duplicate", case=False).sum()))

    l,r = st.columns(2)
    with l:
        q = df.review_band.value_counts().reset_index()
        q.columns = ["band","count"]
        fig = px.bar(q, x="band", y="count", title="Verification / review distribution", text="count")
        fig.update_layout(template="plotly_white", height=360)
        st.plotly_chart(fig, use_container_width=True)
    with r:
        q = df.groupby("search_zone_priority", as_index=False).size()
        q.columns = ["priority","reports"]
        fig = px.bar(q, x="priority", y="reports", title="Coarse search-zone priority signals", text="reports")
        fig.update_layout(template="plotly_white", height=360)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="card"><h3>Coordinator queue</h3>', unsafe_allow_html=True)
    show = [
        "case_code","sighting_id","sighting_zone","sighting_time",
        "source_type","source_verified","verification_score",
        "review_band","search_zone_priority","responder_review_status"
    ]
    st.dataframe(
        df.sort_values(["source_verified","verification_score"], ascending=[True,False])[show],
        use_container_width=True, hide_index=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Sighting Review":
    sid = st.selectbox("Select report", df.sighting_id.astype(str))
    r = df[df.sighting_id.astype(str) == sid].iloc[0]

    a,b,c,d = st.columns(4)
    a.metric("Verification score", f"{r.verification_score:.0f}/100")
    b.metric("Review band", r.review_band)
    c.metric("Source verified", str(r.source_verified))
    d.metric("Zone priority", str(r.search_zone_priority))

    st.markdown('<div class="warning"><b>Do not act on an unverified report.</b> A low or high screening score is not confirmation of a sighting. Authorized responders should independently verify reports and follow established procedures.</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>Report details</h3>', unsafe_allow_html=True)
    st.write(f"**Case:** {r.case_code} • **Report:** {r.sighting_id}")
    st.write(f"**Coarse zone:** {r.sighting_zone} • **Time:** {r.sighting_time}")
    st.write(f"**Source type:** {r.source_type} • **Verification:** {r.source_verified}")
    st.write(f"**Safe reporting channel:** {r.safe_reporting_channel} • **Duplicate check:** {r.duplicate_check}")
    st.write(f"**Responder status:** {r.responder_review_status}")
    st.markdown("</div>", unsafe_allow_html=True)

    factors = ["confidence_score","direction_consistency_score","time_consistency_score","location_consistency_score"]
    q = pd.DataFrame({
        "Signal":[x.replace("_"," ").title() for x in factors],
        "Score":[num(r[x]) for x in factors]
    })
    fig = px.bar(q.sort_values("Score"), x="Score", y="Signal", orientation="h",
                 title="Evidence-consistency signals", text="Score")
    fig.update_layout(template="plotly_white", height=330, xaxis_range=[0,100])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="card"><h3>Human-review notes</h3>', unsafe_allow_html=True)
    notes = calc_score(r)[2]
    if notes:
        for note in notes:
            st.write("• " + note)
    else:
        st.write("• Signals are comparatively consistent, but independent human verification remains required.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Search-Zone Matrix":
    st.markdown('<div class="card"><h3>Coarse search-zone prioritization</h3><p class="small">Zones are synthetic/coarse planning areas. The tool deliberately does not generate public-facing precise coordinates or individual tracking routes.</p></div>', unsafe_allow_html=True)
    q = df.groupby("sighting_zone", as_index=False).agg(
        reports=("sighting_id","count"),
        verified_reports=("source_verified", lambda s: sum(verified(x) for x in s)),
        avg_score=("verification_score","mean")
    )
    q["priority_signal"] = np.where(q.avg_score >= 85, "High", np.where(q.avg_score >= 65, "Moderate", "Low"))
    st.dataframe(q.round(1), use_container_width=True, hide_index=True)

elif page == "Verification Queue":
    st.subheader("Verification-first queue")
    filt = st.multiselect(
        "Show review bands",
        sorted(df.review_band.unique()),
        default=sorted(df.review_band.unique())
    )
    q = df[df.review_band.isin(filt)].copy()
    q["safe_to_act"] = np.where(q.source_verified.apply(verified), "Only after authorized review", "NO — VERIFY FIRST")
    show = [
        "case_code","sighting_id","source_type","source_verified",
        "confidence_score","location_consistency_score",
        "duplicate_check","review_band","safe_to_act"
    ]
    st.dataframe(q.sort_values("verification_score", ascending=False)[show],
                 use_container_width=True, hide_index=True)

elif page == "Local Data Lab":
    st.write("CSV files are processed locally and validated before replacement.")
    st.code(", ".join(REQ), language="text")
    upload = st.file_uploader("Replace local sighting registry", type=["csv"])
    if upload:
        try:
            nd = pd.read_csv(upload)
            missing = [c for c in REQ if c not in nd.columns]
            if missing:
                st.error("Missing required columns: " + ", ".join(missing))
            else:
                nd.to_csv(DATA, index=False)
                st.success(f"Loaded {len(nd):,} local records.")
                st.rerun()
        except Exception as e:
            st.error(str(e))
    st.dataframe(df[REQ], use_container_width=True, hide_index=True)
    export = df.drop(columns=["factor_notes"], errors="ignore").to_csv(index=False).encode()
    st.download_button("Download scored local registry", export,
                       "safereturn_scored_registry.csv", "text/csv")

else:
    st.markdown("""
    <div class="card">
    <h3>Privacy & safety rules</h3>
    <ul>
    <li>Use only synthetic or authorized records.</li>
    <li>Do not store unnecessary names, phone numbers, home addresses, school details, photographs, or precise live-location data.</li>
    <li>Use coarse internal zones instead of public-facing precise locations wherever possible.</li>
    <li>Unverified community reports must never be treated as confirmed sightings.</li>
    <li>Do not publish case details or attempt independent searches, confrontation, or surveillance.</li>
    <li>Use the system only as a support layer for authorized responders and established missing-child procedures.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("SafeReturn Local • 100% local processing • No external APIs • Authorized missing-child coordination decision support")
