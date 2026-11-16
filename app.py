"""
Streamlit Web Dashboard for Universal Multi-Agent Strategy System.
Self-adapts to ANY dataset (Sales, HR, Logistics, Healthcare, Finance, SaaS, Operations).
Run with: streamlit run app.py
"""
import os
import streamlit as st
import pandas as pd
from db import init_db, get_conn
from data_importer import DataImporter, generate_sample_excel_template
from universal_profiler import UniversalDataProfiler, load_any_dataset
from universal_agents import UniversalChiefStrategyOfficer
from data_query_engine import get_active_dataframe, set_active_dataframe, answer_data_query

st.set_page_config(
    page_title="Universal AI Strategy & ERP Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# Sidebar: Universal Data Ingestion
with st.sidebar:
    st.title("⚡ Universal AI Engine")
    st.caption("Self-Adapting Multi-Agent Business Strategist")
    st.markdown("---")

    st.subheader("📥 Ingest Any Dataset")
    uploaded_file = st.file_uploader(
        "Upload ANY Excel, CSV, Parquet, or JSON",
        type=["xlsx", "xls", "csv", "json", "parquet"],
        help="Upload any dataset from any industry (E-commerce, HR, Finance, Operations, Logistics, etc.). The engine automatically auto-tunes itself.",
    )

    replace_data = st.checkbox("Replace previous active dataset", value=True)

    if uploaded_file is not None:
        if st.button("🚀 Ingest & Auto-Tune Engine", use_container_width=True, type="primary"):
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("Profiling dataset, identifying semantic roles & auto-tuning agents..."):
                try:
                    importer = DataImporter()
                    stats = importer.import_file(temp_path, clear_existing=replace_data)
                    st.success(f"Loaded {stats['raw_total_rows']:,} records across {stats['raw_total_columns']} attributes!")
                    st.info(f"Primary Metric Found: **'{stats['primary_metric']}'** | Quality: **{stats['data_quality_score']}/100**")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ingestion Error: {e}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

    st.markdown("---")
    st.subheader("🧪 Load Demo Dataset")
    if st.button("Load Multi-Product ERP Sample", use_container_width=True):
        sample_path = "sample_erp_data.xlsx"
        generate_sample_excel_template(sample_path)
        importer = DataImporter()
        importer.import_file(sample_path, clear_existing=True)
        st.success("Sample loaded & auto-tuned!")
        st.rerun()

    st.markdown("---")
    st.caption("Engine Mode:")
    if os.getenv("GROQ_API_KEY"):
        st.success("🟢 LLM Synthesis: Online (Groq)")
    else:
        st.info("🟡 Engine: Deterministic Mathematical Profiler (Zero-Hallucination Local Mode)")


# Main Dashboard Area
df = get_active_dataframe()

if len(df) == 0:
    st.info("👋 Welcome! Upload **any Excel or CSV dataset** in the sidebar (or click 'Load Demo Dataset') to initiate the self-tuning multi-agent strategy engine.")
    st.stop()

# Header
profiler = UniversalDataProfiler(df)
profile = profiler.get_profile()
pm = profile["semantic_roles"]["primary_metric"]
dims = profile["semantic_roles"]["dimensions"]

st.title("🌐 Universal Multi-Agent Business Strategy Dashboard")
st.caption(f"Active Dataset: **{profile['dataset_name']}** | Rows: **{profile['total_rows']:,}** | Attributes: **{profile['total_columns']}** | Primary Metric: **'{pm}'**")

# Top KPI Metric Row
k1, k2, k3, k4 = st.columns(4)
total_metric_val = df[pm].sum() if pm and pm in df.columns else 0.0
avg_metric_val = df[pm].mean() if pm and pm in df.columns else 0.0

k1.metric("Total Records", f"{profile['total_rows']:,}", f"{profile['total_columns']} Columns")
k2.metric(f"Total {pm or 'Value'}", f"Rs. {total_metric_val:,.2f}" if total_metric_val > 0 else f"{total_metric_val:,.2f}", "Grand Total")
k3.metric(f"Average {pm or 'Value'}", f"Rs. {avg_metric_val:,.2f}" if avg_metric_val > 0 else f"{avg_metric_val:,.2f}", "Mean Baseline")
k4.metric("Data Quality Score", f"{profile['data_quality_score']} / 100", "Completeness Score")

st.markdown("---")

# Strategy Scan Action
col_scan_btn, col_q = st.columns([1, 2])
with col_scan_btn:
    run_scan = st.button("🔍 Run Multi-Agent Strategy Scan", type="primary", use_container_width=True)

if run_scan or "universal_dossier" in st.session_state:
    if run_scan:
        with st.spinner("Self-tuning agents analyzing data distributions, Pareto concentration, and segments..."):
            cso = UniversalChiefStrategyOfficer(df, dataset_name=profile["dataset_name"])
            dossier = cso.run_universal_scan()
            st.session_state["universal_dossier"] = dossier
    else:
        dossier = st.session_state["universal_dossier"]

    score = dossier["business_health_score"]
    color = "green" if score >= 75 else ("orange" if score >= 50 else "red")

    st.markdown(
        f"""
        <div style="background-color: #f8f9fa; padding: 18px; border-radius: 10px; border-left: 8px solid {color}; margin-bottom: 22px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0; color: #1e1e1e;">Executive Business Performance & Resilience Score: <span style="color: {color};">{score} / 100</span></h3>
                    <p style="margin: 5px 0 0 0; color: #555;">Classification: <b>{'OPTIMAL / RESILIENT' if score >= 75 else ('ATTENTION REQUIRED' if score >= 50 else 'OPERATIONAL RISK DETECTED')}</b> | Grounded strictly in factual data</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.9em; color: #777;">Identified Growth / Upside Potential:</div>
                    <div style="font-size: 1.4em; font-weight: bold; color: #0d6efd;">Rs. {dossier['estimated_upside_opportunity']:,.2f}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    t_roadmap, t_driver, t_segment, t_temporal, t_quality, t_explorer = st.tabs([
        "🏢 Executive Roadmap & SWOT",
        "🎯 Primary Value Driver",
        "🧩 Segment Breakdown & Upside",
        "⏱️ Trend & Temporal Velocity",
        "🛡️ Data Integrity & Hygiene",
        "💬 Ask Your Data & Explorer",
    ])

    # 1. Executive Roadmap Tab
    with t_roadmap:
        st.subheader("🎯 3-Tier Strategic Implementation Plan")
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            st.markdown("#### ⚡ Phase 1: Immediate Triage (7 Days)")
            for item in dossier["strategic_roadmap"]["phase_1_immediate_7_days"]:
                st.warning(f"• {item}")
        with c_p2:
            st.markdown("#### 🎯 Phase 2: Tactical Optimization (30 Days)")
            for item in dossier["strategic_roadmap"]["phase_2_tactical_30_days"]:
                st.info(f"• {item}")
        with c_p3:
            st.markdown("#### 🚀 Phase 3: Strategic Scaling (90 Days)")
            for item in dossier["strategic_roadmap"]["phase_3_strategic_90_days"]:
                st.success(f"• {item}")

        st.markdown("---")
        st.subheader("⚖️ Data-Grounded SWOT Matrix (Zero-Hallucination)")
        s1, s2 = st.columns(2)
        with s1:
            st.markdown("##### 🟢 Strengths")
            for x in dossier["swot"]["strengths"]:
                st.write(f"✓ {x}")
            st.markdown("##### 🟡 Opportunities")
            for x in dossier["swot"]["opportunities"]:
                st.write(f"✦ {x}")
        with s2:
            st.markdown("##### 🔴 Weaknesses")
            for x in dossier["swot"]["weaknesses"]:
                st.write(f"✗ {x}")
            st.markdown("##### ⚠️ Threats")
            for x in dossier["swot"]["threats"]:
                st.write(f"▲ {x}")

    # 2. Driver Tab
    with t_driver:
        drv = dossier["primary_driver"]
        st.subheader(f"🎯 Analysis of Primary Metric: '{dossier['primary_metric']}'")
        dc1, dc2, dc3 = st.columns(3)
        dc1.metric("Total Volume", f"Rs. {drv.get('total_value', 0):,.2f}")
        dc2.metric("Median Record Value", f"Rs. {drv.get('median_value', 0):,.2f}")
        dc3.metric("Pareto Concentration (Top 20%)", f"{drv.get('pareto_concentration_pct', 0)}%")

        st.markdown("#### 💡 Strategic Directives")
        for r in drv.get("recommendations", []):
            st.info(r)

    # 3. Segment Tab
    with t_segment:
        seg = dossier["segmentation"]
        st.subheader("🧩 Dimensional Breakdown & Segment Gap Analysis")
        st.markdown(f"**Calculated Revenue Upside from lifting lagging segments:** `Rs. {seg.get('total_upside_potential', 0):,.2f}`")

        for rep in seg.get("dimension_reports", []):
            st.markdown(f"### Dimension: `{rep['dimension']}` ({rep['segment_count']} segments)")
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.write(f"• Top Segment: **{rep['top_segment']}** ({rep['top_segment_share_pct']}% share, Rs. {rep['top_segment_value']:,.2f})")
                st.write(f"• Lagging Segment: **{rep['bottom_segment']}** ({rep['bottom_segment_share_pct']}% share)")
                st.write(f"• Segment Optimization Potential: **Rs. {rep['upside_potential']:,.2f}**")
            with col_r:
                if rep.get("breakdown"):
                    df_b = pd.DataFrame(rep["breakdown"])
                    st.dataframe(df_b, use_container_width=True)

        st.markdown("#### 💡 Segment Directives")
        for r in seg.get("recommendations", []):
            st.info(r)

    # 4. Temporal Tab
    with t_temporal:
        tmp = dossier["temporal"]
        if tmp.get("has_temporal"):
            st.subheader(f"⏱️ Time-Series Dynamics on `{tmp.get('date_column')}`")
            tc1, tc2, tc3 = st.columns(3)
            tc1.metric("Growth Velocity", f"{tmp.get('growth_rate_pct')}%")
            tc2.metric("Peak Period", str(tmp.get("peak_period")), f"Rs. {tmp.get('peak_value', 0):,.2f}")
            tc3.metric("Trough Period", str(tmp.get("trough_period")), f"Rs. {tmp.get('trough_value', 0):,.2f}")

            if tmp.get("monthly_trends"):
                df_trends = pd.DataFrame(tmp["monthly_trends"])
                st.line_chart(df_trends.set_index("period")["sum"])

            st.markdown("#### 💡 Temporal Directives")
            for r in tmp.get("recommendations", []):
                st.info(r)
        else:
            st.info("No temporal date columns detected in this dataset.")

    # 5. Quality Tab
    with t_quality:
        dq = dossier["data_quality"]
        st.subheader("🛡️ Data Architecture & Hygiene Audit")
        qc1, qc2, qc3 = st.columns(3)
        qc1.metric("Quality Score", f"{dq.get('quality_score')}/100")
        qc2.metric("Missing Value Warnings", len(dq.get("missing_columns", [])))
        qc3.metric("Zero-Fill Anomalies", len(dq.get("zero_fill_warnings", [])))

        for r in dq.get("recommendations", []):
            st.warning(r)

        st.markdown("#### 📋 Column Inferred Types & Metadata")
        df_cols = pd.DataFrame([
            {"Column": c, "Inferred Role": v["inferred_type"], "Missing %": v["missing_pct"], "Unique Values": v["unique_count"]}
            for c, v in profile["columns"].items()
        ])
        st.dataframe(df_cols, use_container_width=True)

    # 6. Explorer & Zero-Hallucination Query Tab
    with t_explorer:
        st.subheader("💬 Ask Your Data (Zero Hallucinations)")
        st.caption("Ask any question. The engine runs computations directly on the dataset to provide exact factual numbers.")

        user_q = st.text_input("Enter your question:", placeholder="e.g. What is the total sales? Which category is highest? Average price?")
        if user_q:
            with st.spinner("Computing factual answer from data..."):
                answer = answer_data_query(user_q, df)
                st.success(answer)

        st.markdown("---")
        st.subheader("📋 Raw Data Explorer")
        st.dataframe(df.head(200), use_container_width=True)

else:
    st.info("👆 Click **'Run Multi-Agent Strategy Scan'** to analyze the loaded dataset.")
