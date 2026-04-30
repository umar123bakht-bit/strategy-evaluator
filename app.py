import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from utils.database import (
    init_db, add_brand, get_brands, get_brand, update_brand, delete_brand,
    save_analysis, get_analyses, get_analysis, delete_analysis,
)
from utils.parser import extract_text_from_file
from utils.analyzer import analyze_strategy

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Strategy Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
    padding: 2rem 2.5rem; border-radius: 14px; color: white; margin-bottom: 1.8rem;
  }
  .hero h1 { margin: 0; font-size: 2rem; }
  .hero p  { margin: 0.4rem 0 0; opacity: .85; }
  .kpi-box {
    background: white; border: 1px solid #e0e7f0; border-radius: 10px;
    padding: 1.1rem; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,.05);
  }
  .kpi-box .val { font-size: 2rem; font-weight: 700; }
  .kpi-box .lbl { font-size: .8rem; color: #666; margin-top: .2rem; }
  .brand-row {
    background: #f4f8fd; border-left: 4px solid #2d6a9f;
    padding: .9rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: .8rem;
  }
  .verdict-chip {
    display: inline-block; padding: .25rem .9rem; border-radius: 20px;
    font-weight: 700; font-size: .8rem;
  }
  .rec-item {
    padding: .55rem .8rem .55rem 1rem; margin: .45rem 0;
    border-radius: 0 6px 6px 0;
  }
</style>
""", unsafe_allow_html=True)

# ── DB init ───────────────────────────────────────────────────────────────────
init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(s):
    if s >= 80: return "#27ae60"
    if s >= 65: return "#2980b9"
    if s >= 50: return "#f39c12"
    return "#e74c3c"


def verdict_color(v):
    return {
        "Highly Effective": "#27ae60",
        "Effective":        "#2980b9",
        "Needs Improvement":"#f39c12",
        "Ineffective":      "#e74c3c",
    }.get(v, "#666")


def radar_chart(dims):
    labels = [d["label"] for d in dims] + [dims[0]["label"]]
    scores = [d["score"] for d in dims] + [dims[0]["score"]]
    fig = go.Figure(go.Scatterpolar(
        r=scores, theta=labels, fill="toself",
        fillcolor="rgba(45,106,159,.18)",
        line=dict(color="#2d6a9f", width=2),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=390,
        margin=dict(l=55, r=55, t=35, b=35),
    )
    return fig


def bar_chart(dims):
    labels = [d["label"] for d in dims]
    scores = [d["score"] for d in dims]
    fig = go.Figure(go.Bar(
        x=scores, y=labels, orientation="h",
        marker_color=[score_color(s) for s in scores],
        text=[f"{s}/100" for s in scores], textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 115], showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(autorange="reversed"),
        height=340, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=55, t=15, b=15),
    )
    return fig


def gauge_chart(score):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        gauge={
            "axis": {"range": [0, 100]},
            "bar":  {"color": score_color(score)},
            "steps": [
                {"range": [0, 50],   "color": "#fde8e8"},
                {"range": [50, 65],  "color": "#fef3cd"},
                {"range": [65, 80],  "color": "#d1ecf1"},
                {"range": [80, 100], "color": "#d4edda"},
            ],
        },
    ))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=30, b=10))
    return fig


def render_results(results):
    """Render a full analysis result dict."""
    vc = verdict_color(results["verdict"])

    # ── Score + summary ──
    col_g, col_s = st.columns([1, 2])
    with col_g:
        st.plotly_chart(gauge_chart(results["overall_score"]), use_container_width=True)
        st.markdown(
            f"<div style='text-align:center'>"
            f"<span class='verdict-chip' style='background:{vc}18;color:{vc};border:1px solid {vc}'>"
            f"{results['verdict']}</span></div>",
            unsafe_allow_html=True,
        )
    with col_s:
        st.markdown("**Executive Summary**")
        st.markdown(results["executive_summary"])
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Top Strengths**")
            for s in results.get("top_strengths", []):
                st.markdown(f"✅ {s}")
        with col_b:
            st.markdown("**Critical Risks**")
            for r in results.get("critical_risks", []):
                st.markdown(f"⚠️ {r}")

    # ── Charts ──
    st.markdown("---")
    dims_list = [{"label": v["label"], "score": v["score"]} for v in results["dimensions"].values()]
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Dimension Radar")
        st.plotly_chart(radar_chart(dims_list), use_container_width=True)
    with c2:
        st.subheader("Dimension Scores")
        st.plotly_chart(bar_chart(dims_list), use_container_width=True)

    # ── Detailed breakdown ──
    st.markdown("---")
    st.subheader("Detailed Breakdown")
    dim_items = list(results["dimensions"].items())
    for i in range(0, len(dim_items), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(dim_items):
                break
            key, dim = dim_items[i + j]
            sc = score_color(dim["score"])
            with col:
                with st.expander(f"{dim['label']} — {dim['score']}/100", expanded=True):
                    st.markdown(
                        f"**Score:** <span style='color:{sc};font-weight:700'>{dim['score']}/100</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(dim["feedback"])
                    if dim.get("strengths"):
                        st.markdown("**Strengths:**")
                        for s in dim["strengths"]:
                            st.markdown(f"✅ {s}")
                    if dim.get("improvements"):
                        st.markdown("**Improvements:**")
                        for imp in dim["improvements"]:
                            st.markdown(f"🔧 {imp}")

    # ── Recommendations ──
    st.markdown("---")
    st.subheader("Recommendations")
    priority_color = {"High": "#e74c3c", "Medium": "#f39c12", "Low": "#27ae60"}
    for rec in results.get("recommendations", []):
        pc = priority_color.get(rec["priority"], "#666")
        st.markdown(
            f"<div class='rec-item' style='border-left:3px solid {pc};background:{pc}10'>"
            f"<span style='color:{pc};font-weight:700;font-size:.78rem'>{rec['priority'].upper()} PRIORITY</span><br>"
            f"{rec['action']}</div>",
            unsafe_allow_html=True,
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 📊 Strategy Evaluator")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "🏢 Brands", "🔍 Analyze", "📋 History"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
_brands   = get_brands()
_analyses = get_analyses()
st.sidebar.markdown(f"**{len(_brands)}** brand(s) · **{len(_analyses)}** analysis(es)")


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown(
        "<div class='hero'><h1>📊 Strategy Evaluator</h1>"
        "<p>AI-powered strategy effectiveness analysis for your brands</p></div>",
        unsafe_allow_html=True,
    )

    # KPI row
    avg_score = (
        sum(a["overall_score"] for a in _analyses) / len(_analyses)
        if _analyses else 0
    )
    effective_count = sum(
        1 for a in _analyses if a["verdict"] in ("Highly Effective", "Effective")
    )
    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl, color in [
        (c1, len(_brands),       "Brands",              "#2d6a9f"),
        (c2, len(_analyses),     "Analyses Run",         "#2d6a9f"),
        (c3, f"{avg_score:.0f}", "Avg Score",            score_color(avg_score) if _analyses else "#999"),
        (c4, effective_count,    "Effective Strategies", "#27ae60"),
    ]:
        col.markdown(
            f"<div class='kpi-box'><div class='val' style='color:{color}'>{val}</div>"
            f"<div class='lbl'>{lbl}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if not _analyses:
        st.info("No analyses yet. Add brands → upload a deck → run your first analysis.")
    else:
        col_l, col_r = st.columns([2, 1])

        with col_l:
            st.subheader("Recent Analyses")
            for a in _analyses[:8]:
                sc = score_color(a["overall_score"])
                vc = verdict_color(a["verdict"])
                st.markdown(
                    f"<div class='brand-row'>"
                    f"<strong>{a['deck_name']}</strong> · <em>{a['brand_name']}</em>"
                    f"<span style='float:right;color:{sc};font-weight:700'>{a['overall_score']}/100</span><br>"
                    f"<small style='color:#666'>{a['industry']} · {a['created_at'][:16]}</small>"
                    f"<span style='float:right;color:{vc};font-size:.8rem'>{a['verdict']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with col_r:
            st.subheader("Score Distribution")
            buckets = {"Ineffective\n(0–49)": 0, "Needs Work\n(50–64)": 0,
                       "Effective\n(65–79)": 0, "Highly Eff.\n(80–100)": 0}
            for a in _analyses:
                s = a["overall_score"]
                if s < 50:   buckets["Ineffective\n(0–49)"] += 1
                elif s < 65: buckets["Needs Work\n(50–64)"] += 1
                elif s < 80: buckets["Effective\n(65–79)"] += 1
                else:        buckets["Highly Eff.\n(80–100)"] += 1
            fig = px.pie(
                values=list(buckets.values()),
                names=list(buckets.keys()),
                color_discrete_sequence=["#e74c3c", "#f39c12", "#2980b9", "#27ae60"],
                hole=.35,
            )
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    if _brands:
        st.markdown("---")
        st.subheader("Brand Overview")
        for brand in _brands:
            brand_analyses = [a for a in _analyses if a["brand_name"] == brand["name"]]
            avg = (
                sum(a["overall_score"] for a in brand_analyses) / len(brand_analyses)
                if brand_analyses else None
            )
            ca, cb, cc = st.columns([3, 1, 1])
            ca.markdown(f"**{brand['name']}** · {brand['industry']}")
            cb.markdown(f"Analyses: **{len(brand_analyses)}**")
            if avg is not None:
                cc.markdown(
                    f"Avg: <span style='color:{score_color(avg)};font-weight:700'>{avg:.0f}</span>",
                    unsafe_allow_html=True,
                )
            else:
                cc.markdown("No analyses yet")


# ══════════════════════════════════════════════════════════════════════════════
# BRANDS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏢 Brands":
    st.title("Brand Management")
    tab_add, tab_all = st.tabs(["➕ Add Brand", "📋 All Brands"])

    INDUSTRIES = [
        "Technology", "Retail & E-commerce", "Food & Beverage",
        "Fashion & Apparel", "Healthcare", "Finance & Banking",
        "Real Estate", "Education", "Entertainment & Media",
        "Automotive", "Travel & Hospitality", "Beauty & Personal Care",
        "Sports & Fitness", "Manufacturing", "Other",
    ]

    with tab_add:
        st.subheader("Register a New Brand")
        with st.form("add_brand"):
            c1, c2 = st.columns(2)
            with c1:
                b_name    = st.text_input("Brand Name *", placeholder="e.g., Acme Corp")
                b_industry = st.selectbox("Industry *", INDUSTRIES)
            with c2:
                b_market  = st.text_input("Target Market", placeholder="e.g., Young professionals 25–35")
                b_desc    = st.text_area("Brand Description", placeholder="Values, positioning, differentiators…", height=100)

            if st.form_submit_button("Add Brand", type="primary"):
                if not b_name.strip():
                    st.error("Brand name is required.")
                elif add_brand(b_name.strip(), b_industry, b_desc, b_market):
                    st.success(f"Brand '{b_name}' added!")
                    st.rerun()
                else:
                    st.error(f"A brand named '{b_name}' already exists.")

    with tab_all:
        brands = get_brands()
        if not brands:
            st.info("No brands yet.")
        for brand in brands:
            with st.expander(f"🏢 {brand['name']} — {brand['industry']}"):
                edit_key = f"edit_{brand['id']}"
                if st.session_state.get(edit_key):
                    with st.form(f"edit_form_{brand['id']}"):
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            new_name     = st.text_input("Brand Name", value=brand["name"])
                            new_industry = st.selectbox("Industry", INDUSTRIES, index=INDUSTRIES.index(brand["industry"]) if brand["industry"] in INDUSTRIES else 0)
                        with ec2:
                            new_market = st.text_input("Target Market", value=brand.get("target_market") or "")
                            new_desc   = st.text_area("Description", value=brand.get("description") or "", height=80)
                        sc1, sc2 = st.columns(2)
                        if sc1.form_submit_button("Save", type="primary"):
                            update_brand(brand["id"], new_name, new_industry, new_desc, new_market)
                            st.session_state[edit_key] = False
                            st.rerun()
                        if sc2.form_submit_button("Cancel"):
                            st.session_state[edit_key] = False
                            st.rerun()
                else:
                    dc1, dc2 = st.columns([3, 1])
                    with dc1:
                        st.markdown(f"**Industry:** {brand['industry']}")
                        if brand.get("target_market"):
                            st.markdown(f"**Target Market:** {brand['target_market']}")
                        if brand.get("description"):
                            st.markdown(f"**Description:** {brand['description']}")
                        st.markdown(f"**Added:** {brand['created_at'][:10]}")
                        st.markdown(f"**Analyses:** {len(get_analyses(brand['id']))}")
                    with dc2:
                        if st.button("✏️ Edit", key=f"btn_edit_{brand['id']}"):
                            st.session_state[edit_key] = True
                            st.rerun()
                        if st.button("🗑️ Delete", key=f"btn_del_{brand['id']}"):
                            delete_brand(brand["id"])
                            st.success("Brand deleted.")
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Analyze":
    st.title("Analyze Strategy Deck")

    brands = get_brands()
    if not brands:
        st.warning("Add at least one brand before analyzing.")
        st.stop()

    c1, c2 = st.columns([1, 2])
    with c1:
        brand_map = {b["name"]: b["id"] for b in brands}
        sel_name  = st.selectbox("Select Brand", list(brand_map.keys()))
        sel_brand = get_brand(brand_map[sel_name])
        st.markdown(
            f"<div class='brand-row'><strong>{sel_brand['name']}</strong><br>"
            f"<small>{sel_brand['industry']}</small>"
            + (f"<br><small style='color:#555'>{sel_brand['target_market']}</small>" if sel_brand.get("target_market") else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    with c2:
        uploaded = st.file_uploader(
            "Upload Strategy Deck (PDF or PPTX)",
            type=["pdf", "pptx"],
            help="Max 50 MB",
        )

    if uploaded:
        st.markdown(f"**File:** {uploaded.name} &nbsp;|&nbsp; {uploaded.size / 1024:.1f} KB")

        if st.button("🔍 Run Analysis", type="primary", use_container_width=True):
            with st.spinner("Extracting slide content…"):
                try:
                    raw = uploaded.read()
                    content = extract_text_from_file(raw, uploaded.name)
                    if not content.strip():
                        st.error("No readable text found. Ensure the file isn't image-only.")
                        st.stop()
                    st.success(f"Extracted {len(content.split())} words from {uploaded.name}.")
                except Exception as e:
                    st.error(f"Parse error: {e}")
                    st.stop()

            with st.spinner("AI is evaluating your strategy… (15–30 seconds)"):
                try:
                    results = analyze_strategy(
                        brand_name=sel_brand["name"],
                        industry=sel_brand["industry"],
                        brand_description=sel_brand.get("description", ""),
                        target_market=sel_brand.get("target_market", ""),
                        deck_content=content,
                        deck_name=uploaded.name,
                    )
                except Exception as e:
                    st.error(f"Analysis error: {e}")
                    st.stop()

            aid = save_analysis(
                brand_id=sel_brand["id"],
                deck_name=uploaded.name,
                overall_score=results["overall_score"],
                verdict=results["verdict"],
                results_json=results,
            )
            st.success("Analysis complete! Results saved to History.")
            st.session_state["last_results"] = results

    if "last_results" in st.session_state:
        st.markdown("---")
        st.subheader("Analysis Results")
        render_results(st.session_state["last_results"])


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 History":
    st.title("Analysis History")

    brands = get_brands()
    filter_opt = st.selectbox("Filter by Brand", ["All Brands"] + [b["name"] for b in brands])

    if filter_opt == "All Brands":
        all_analyses = get_analyses()
    else:
        bid = next(b["id"] for b in brands if b["name"] == filter_opt)
        all_analyses = get_analyses(bid)

    if not all_analyses:
        st.info("No analyses found.")
    else:
        st.markdown(f"**{len(all_analyses)} result(s)**")
        for a in all_analyses:
            sc = score_color(a["overall_score"])
            vc = verdict_color(a["verdict"])
            header = f"📄 {a['deck_name']}  ·  {a['brand_name']}  ·  {a['overall_score']}/100"
            with st.expander(header):
                results = json.loads(a["results_json"])

                mc1, mc2, mc3 = st.columns([1, 1, 2])
                with mc1:
                    st.metric("Overall Score", f"{a['overall_score']}/100")
                with mc2:
                    st.markdown(
                        f"**Verdict**<br><span style='color:{vc};font-weight:700'>{a['verdict']}</span>",
                        unsafe_allow_html=True,
                    )
                with mc3:
                    st.markdown(f"**Brand:** {a['brand_name']} · {a['industry']}")
                    st.markdown(f"**Date:** {a['created_at'][:16]}")

                st.markdown(results.get("executive_summary", ""))

                dims_list = [{"label": v["label"], "score": v["score"]} for v in results["dimensions"].values()]
                st.plotly_chart(bar_chart(dims_list), use_container_width=True)

                st.markdown("**Top Recommendations:**")
                pc = {"High": "#e74c3c", "Medium": "#f39c12", "Low": "#27ae60"}
                for rec in results.get("recommendations", [])[:3]:
                    c = pc.get(rec["priority"], "#666")
                    st.markdown(
                        f"<div class='rec-item' style='border-left:3px solid {c};background:{c}10'>"
                        f"<span style='color:{c};font-weight:700;font-size:.78rem'>{rec['priority'].upper()}</span> {rec['action']}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                if st.button("🗑️ Delete this analysis", key=f"del_analysis_{a['id']}"):
                    delete_analysis(a["id"])
                    st.rerun()
