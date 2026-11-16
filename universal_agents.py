"""
Universal Multi-Agent Strategic Intelligence Engine.
Self-tunes to ANY dataset (Sales, E-commerce, HR, Finance, Operations, Logistics, Healthcare, SaaS)
without hallucinating rigid domain concepts or mock schemas.
"""
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from universal_profiler import UniversalDataProfiler, clean_numeric_value


class DataQualityAgent:
    name = "Data Integrity & Hygiene Specialist"
    role = "Data Cleansing, Anomaly Detection & Type Verification"

    def scan(self, df: pd.DataFrame, profile: dict) -> dict:
        total_rows = profile["total_rows"]
        total_cols = profile["total_columns"]
        quality_score = profile["data_quality_score"]

        missing_summary = []
        zero_fill_warnings = []
        outlier_warnings = []

        for col, stats in profile["columns"].items():
            if stats["missing_pct"] > 5.0:
                missing_summary.append({
                    "column": col,
                    "missing_count": stats["missing_count"],
                    "missing_pct": stats["missing_pct"],
                })
            if stats.get("zero_count", 0) > (total_rows * 0.3) and stats["inferred_type"] == "numeric":
                zero_fill_warnings.append({
                    "column": col,
                    "zero_count": stats["zero_count"],
                    "zero_pct": round((stats["zero_count"] / max(1, total_rows)) * 100, 1),
                })
            if stats.get("outlier_count", 0) > 0:
                outlier_warnings.append({
                    "column": col,
                    "outlier_count": stats["outlier_count"],
                })

        recommendations = []
        if zero_fill_warnings:
            cols = ", ".join([f"'{x['column']}' ({x['zero_pct']}% zeros)" for x in zero_fill_warnings[:2]])
            recommendations.append(f"DATA TRAP DETECTED: Column(s) {cols} have excessive zero-values. Verify if pricing/revenue metrics were formatted with symbols or missing.")
        if missing_summary:
            cols = ", ".join([f"'{x['column']}' ({x['missing_pct']}% missing)" for x in missing_summary[:2]])
            recommendations.append(f"DATA COMPLETENESS: Fill missing values for {cols} using forward-fill or median imputation.")
        if not recommendations:
            recommendations.append("Data hygiene is robust with strong completeness across all key attributes.")

        return {
            "quality_score": quality_score,
            "total_records": total_rows,
            "total_attributes": total_cols,
            "missing_columns": missing_summary,
            "zero_fill_warnings": zero_fill_warnings,
            "outlier_warnings": outlier_warnings,
            "recommendations": recommendations,
        }


class PrimaryDriverAgent:
    name = "Key Performance & Value Driver Agent"
    role = "Primary Metric Optimization & Distribution Analysis"

    def scan(self, df: pd.DataFrame, profile: dict) -> dict:
        primary_metric = profile["semantic_roles"]["primary_metric"]
        if not primary_metric or primary_metric not in df.columns:
            return {"error": "No primary numeric metric identified."}

        series = df[primary_metric].dropna()
        if len(series) == 0:
            return {"error": f"Primary metric '{primary_metric}' has no numeric values."}

        total_val = float(series.sum())
        mean_val = float(series.mean())
        median_val = float(series.median())
        std_val = float(series.std()) if len(series) > 1 else 0.0
        max_val = float(series.max())
        min_val = float(series.min())

        # Pareto Concentration Analysis
        sorted_s = series.sort_values(ascending=False)
        top_20_count = max(1, int(len(sorted_s) * 0.2))
        top_20_sum = float(sorted_s.iloc[:top_20_count].sum())
        pareto_pct = round((top_20_sum / max(1e-6, total_val)) * 100, 1)

        recommendations = []
        if pareto_pct >= 70:
            recommendations.append(
                f"HIGH CONCENTRATION: The top 20% of records generate {pareto_pct}% of total '{primary_metric}' (Pareto skew). "
                "Protect top performers with dedicated account strategies while creating programs to elevate mid-tier performance."
            )
        elif pareto_pct <= 35:
            recommendations.append(
                f"DIFFUSE SPREAD: '{primary_metric}' is widely distributed (top 20% accounts for only {pareto_pct}%). "
                "Opportunity to create premium tiers or bundled offerings to establish high-ticket leaders."
            )

        if mean_val > 0 and (std_val / mean_val) > 1.2:
            recommendations.append(
                f"VOLATILITY WARNING: High coefficient of variation detected in '{primary_metric}'. Standardize operational baselines to stabilize variance."
            )

        return {
            "metric_name": primary_metric,
            "total_value": total_val,
            "mean_value": round(mean_val, 2),
            "median_value": round(median_val, 2),
            "min_value": min_val,
            "max_value": max_val,
            "pareto_concentration_pct": pareto_pct,
            "recommendations": recommendations,
        }


class SegmentationStrategistAgent:
    name = "Dimensional & Segment Strategist"
    role = "Categorical Breakdown, Cross-Tabulation & Segment Upside"

    def scan(self, df: pd.DataFrame, profile: dict) -> dict:
        primary_metric = profile["semantic_roles"]["primary_metric"]
        dimensions = profile["semantic_roles"]["dimensions"]

        if not dimensions or not primary_metric or primary_metric not in df.columns:
            return {"dimension_analysis": [], "recommendations": ["No categorical dimensions detected for segmentation."]}

        dimension_reports = []
        all_recommendations = []
        total_upside_potential = 0.0

        for dim in dimensions[:3]:  # Analyze top 3 dimensions
            try:
                grouped = df.groupby(dim)[primary_metric].agg(["count", "sum", "mean"]).reset_index()
                grouped = grouped.sort_values(by="sum", ascending=False)
                grouped["pct_share"] = round((grouped["sum"] / max(1e-6, grouped["sum"].sum())) * 100, 1)

                top_segment = grouped.iloc[0]
                bottom_segment = grouped.iloc[-1]
                median_mean = float(grouped["mean"].median())

                # Calculate monetary upside if bottom segments are lifted to median
                lift_potential = sum(
                    max(0.0, (median_mean - row["mean"]) * row["count"])
                    for _, row in grouped.iterrows() if row["mean"] < median_mean
                )
                total_upside_potential += lift_potential

                seg_dict = {
                    "dimension": dim,
                    "segment_count": len(grouped),
                    "top_segment": str(top_segment[dim]),
                    "top_segment_share_pct": float(top_segment["pct_share"]),
                    "top_segment_value": float(top_segment["sum"]),
                    "bottom_segment": str(bottom_segment[dim]),
                    "bottom_segment_share_pct": float(bottom_segment["pct_share"]),
                    "upside_potential": round(lift_potential, 2),
                    "breakdown": grouped.head(6).to_dict(orient="records"),
                }
                dimension_reports.append(seg_dict)

                if top_segment["pct_share"] >= 45:
                    all_recommendations.append(
                        f"SEGMENT DOMINANCE in '{dim}': '{top_segment[dim]}' commands {top_segment['pct_share']}% of {primary_metric}. "
                        f"Target under-penetrated segments like '{bottom_segment[dim]}' to balance portfolio risk."
                    )
                else:
                    all_recommendations.append(
                        f"GROWTH OPPORTUNITY in '{dim}': Lifting below-median segments toward average performance unlocks an estimated Rs. {lift_potential:,.2f} in value."
                    )
            except Exception:
                continue

        return {
            "dimension_reports": dimension_reports,
            "total_upside_potential": total_upside_potential,
            "recommendations": all_recommendations,
        }


class TemporalStrategistAgent:
    name = "Temporal & Velocity Strategist"
    role = "Trend Analysis, Seasonality & Growth Trajectory"

    def scan(self, df: pd.DataFrame, profile: dict) -> dict:
        temporal_cols = profile["semantic_roles"]["temporal"]
        primary_metric = profile["semantic_roles"]["primary_metric"]

        if not temporal_cols or not primary_metric or primary_metric not in df.columns:
            return {"has_temporal": False, "recommendations": ["No temporal date columns detected for trend analysis."]}

        date_col = temporal_cols[0]
        try:
            df_temp = df[[date_col, primary_metric]].dropna().copy()
            df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors="coerce")
            df_temp = df_temp.dropna().sort_values(by=date_col)

            # Resample by month
            df_temp["period"] = df_temp[date_col].dt.to_period("M").astype(str)
            monthly = df_temp.groupby("period")[primary_metric].agg(["sum", "count"]).reset_index()

            if len(monthly) >= 2:
                first_period_val = monthly.iloc[0]["sum"]
                last_period_val = monthly.iloc[-1]["sum"]
                growth_rate = round(((last_period_val - first_period_val) / max(1e-6, first_period_val)) * 100, 1)

                peak_month = monthly.sort_values(by="sum", ascending=False).iloc[0]
                trough_month = monthly.sort_values(by="sum").iloc[0]

                recommendations = []
                if growth_rate > 0:
                    recommendations.append(f"GROWTH TRAJECTORY: Total '{primary_metric}' grew by {growth_rate}% from {monthly.iloc[0]['period']} to {monthly.iloc[-1]['period']}.")
                else:
                    recommendations.append(f"CONTRACTION ALERT: Total '{primary_metric}' declined by {abs(growth_rate)}% over the measured timeframe. Audit recent market conditions.")

                recommendations.append(
                    f"SEASONAL SPREAD: Peak period was {peak_month['period']} (Rs. {peak_month['sum']:,.2f}) vs low of {trough_month['period']} (Rs. {trough_month['sum']:,.2f}). Prepare buffer capacity for peak periods."
                )

                return {
                    "has_temporal": True,
                    "date_column": date_col,
                    "period_count": len(monthly),
                    "growth_rate_pct": growth_rate,
                    "peak_period": str(peak_month["period"]),
                    "peak_value": float(peak_month["sum"]),
                    "trough_period": str(trough_month["period"]),
                    "trough_value": float(trough_month["sum"]),
                    "monthly_trends": monthly.tail(12).to_dict(orient="records"),
                    "recommendations": recommendations,
                }
        except Exception:
            pass

        return {"has_temporal": False, "recommendations": ["Temporal parsing completed."]}


class UniversalChiefStrategyOfficer:
    """Consolidates universal multi-agent telemetry into an Executive Strategy Report."""

    def __init__(self, df: pd.DataFrame, dataset_name: str = "Uploaded Dataset"):
        self.df = df
        self.profiler = UniversalDataProfiler(df, dataset_name=dataset_name)
        self.profile = self.profiler.get_profile()

        self.quality_agent = DataQualityAgent()
        self.driver_agent = PrimaryDriverAgent()
        self.segment_agent = SegmentationStrategistAgent()
        self.temporal_agent = TemporalStrategistAgent()

    def run_universal_scan(self) -> dict:
        """Runs the complete multi-agent scan across all dataset attributes."""
        quality_scan = self.quality_agent.scan(self.df, self.profile)
        driver_scan = self.driver_agent.scan(self.df, self.profile)
        segment_scan = self.segment_agent.scan(self.df, self.profile)
        temporal_scan = self.temporal_agent.scan(self.df, self.profile)

        # Unified Mathematical Health Index (0-100)
        q_score = quality_scan.get("quality_score", 80.0)
        pareto = driver_scan.get("pareto_concentration_pct", 50.0)
        # Moderate pareto (40-60%) is healthy; extreme (>75%) is high risk
        conc_score = max(20.0, 100.0 - (max(0.0, pareto - 50.0) * 1.5))
        growth = temporal_scan.get("growth_rate_pct", 0.0)
        growth_score = min(100.0, max(40.0, 70.0 + growth * 0.5))

        health_index = round((q_score * 0.35) + (conc_score * 0.35) + (growth_score * 0.30), 1)

        # Dynamic SWOT Generation
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        pm = self.profile["semantic_roles"]["primary_metric"]
        if driver_scan.get("total_value", 0) > 0:
            strengths.append(f"Recorded volume of Rs. {driver_scan['total_value']:,.2f} across {self.profile['total_rows']:,} records in '{pm}'.")

        if quality_scan.get("quality_score", 0) >= 85:
            strengths.append(f"High data hygiene integrity ({quality_scan['quality_score']}/100) supporting dependable decision making.")
        else:
            weaknesses.append("Data completeness gaps detected in key attributes.")

        if quality_scan.get("zero_fill_warnings"):
            weaknesses.append("Excessive zero values in numeric attributes indicate possible uncaptured metrics or currency format errors.")

        if segment_scan.get("total_upside_potential", 0) > 0:
            opportunities.append(f"Elevating under-performing segments to median benchmark yields an estimated Rs. {segment_scan['total_upside_potential']:,.2f} in upside.")

        opportunities.append(f"Implement targeted resource allocation towards high-performing {', '.join(self.profile['semantic_roles']['dimensions'][:2])} dimensions.")

        if driver_scan.get("pareto_concentration_pct", 0) >= 70:
            threats.append(f"High dependency vulnerability: Top 20% of accounts generate {driver_scan['pareto_concentration_pct']}% of {pm}.")

        if temporal_scan.get("growth_rate_pct", 0) < 0:
            threats.append(f"Negative growth trajectory ({temporal_scan['growth_rate_pct']}%) observed across recent measurement cycles.")

        # 3-Tier Execution Roadmap
        phase_1 = []
        phase_2 = []
        phase_3 = []

        # Phase 1: Immediate Triage (Next 7 Days)
        if quality_scan.get("zero_fill_warnings"):
            phase_1.append("Correct numeric column formatting and resolve zero-value anomalies.")
        if driver_scan.get("pareto_concentration_pct", 0) >= 65:
            phase_1.append(f"Secure relationships and service SLAs with top 20% value drivers in '{pm}'.")
        if not phase_1:
            phase_1.append("Audit baseline distribution and establish weekly KPI monitoring thresholds.")

        # Phase 2: Tactical Moves (Days 8 to 30)
        if segment_scan.get("dimension_reports"):
            top_dim = segment_scan["dimension_reports"][0]
            phase_2.append(f"Deploy targeted expansion campaign for under-performing segments in '{top_dim['dimension']}' to capture upside.")
        phase_2.append("Standardize margin and discount guidelines to reduce cross-segment performance variance.")

        # Phase 3: Strategic Scaling (Days 31 to 90)
        phase_3.append("Automate predictive monitoring on key operational dimensions.")
        phase_3.append("Diversify customer and product portfolio to lower Pareto concentration risk.")

        upside = segment_scan.get("total_upside_potential", 0.0)

        dossier = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_name": self.profile["dataset_name"],
            "total_records": self.profile["total_rows"],
            "total_columns": self.profile["total_columns"],
            "primary_metric": pm,
            "business_health_score": health_index,
            "estimated_upside_opportunity": upside,
            "data_quality": quality_scan,
            "primary_driver": driver_scan,
            "segmentation": segment_scan,
            "temporal": temporal_scan,
            "swot": {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "opportunities": opportunities,
                "threats": threats,
            },
            "strategic_roadmap": {
                "phase_1_immediate_7_days": phase_1,
                "phase_2_tactical_30_days": phase_2,
                "phase_3_strategic_90_days": phase_3,
            },
        }

        return dossier

    def generate_executive_narrative(self, dossier: dict) -> str:
        """Generates boardroom-grade executive strategic assessment without hallucinations."""
        # Check if Groq client is usable
        has_groq = False
        try:
            from config import get_client, MODEL
            client = get_client()
            has_groq = True
        except Exception:
            has_groq = False

        if has_groq:
            prompt = f"""
You are the Chief Strategy Officer analyzing an enterprise dataset.
Produce an incisive, boardroom-grade Executive Strategic Briefing based strictly on the factual multi-agent data telemetry below.
DO NOT hallucinate fictional entities (no tomatoes or grocery items unless they explicitly exist in the dataset!).
Address the actual discovered primary metric ({dossier['primary_metric']}) and actual dimensions.

Format your response with:
1. Executive Performance Rating & Health Score ({dossier['business_health_score']}/100)
2. Primary Metric & Pareto Driver Analysis
3. Segment Performance & Profit/Value Optimization
4. Operational Risks & SWOT Matrix
5. Prioritized 7-Day / 30-Day / 90-Day Execution Directives

Factual Dossier:
{json.dumps(dossier, indent=2, default=str)}
"""
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                return resp.choices[0].message.content or ""
            except Exception:
                pass

        # Algorithmic narrative
        s = dossier["swot"]
        r = dossier["strategic_roadmap"]
        q = dossier["data_quality"]
        d = dossier["primary_driver"]
        seg = dossier["segmentation"]
        t = dossier["temporal"]

        return f"""
================================================================================
           UNIVERSAL MULTI-AGENT STRATEGIC BUSINESS ASSESSMENT
================================================================================
Dataset: {dossier['dataset_name']} ({dossier['total_records']:,} rows, {dossier['total_columns']} columns)
Primary Discovered Metric: {dossier['primary_metric']}
Business Performance & Resilience Score: {dossier['business_health_score']} / 100
Identified Upside Realization Potential: Rs. {dossier['estimated_upside_opportunity']:,.2f}

--------------------------------------------------------------------------------
1. EXECUTIVE DIAGNOSTIC SUMMARY
--------------------------------------------------------------------------------
• Health Status: {'OPTIMAL' if dossier['business_health_score'] >= 75 else ('ATTENTION REQUIRED' if dossier['business_health_score'] >= 50 else 'HIGH OPERATIONAL RISK')}
• Volume & Total: Rs. {d.get('total_value', 0):,.2f} recorded in '{dossier['primary_metric']}' (Mean: Rs. {d.get('mean_value', 0):,.2f}, Median: Rs. {d.get('median_value', 0):,.2f}).
• Pareto Skew: {d.get('pareto_concentration_pct', 0)}% of value is driven by the top 20% of records.
• Data Quality Rating: {q.get('quality_score', 0)}/100 across {dossier['total_columns']} attributes.

--------------------------------------------------------------------------------
2. DATA-DERIVED SWOT MATRIX (Zero-Hallucination)
--------------------------------------------------------------------------------
[+] STRENGTHS:
{chr(10).join(['  • ' + x for x in s['strengths']]) if s['strengths'] else '  • Established transaction baseline active.'}

[-] WEAKNESSES:
{chr(10).join(['  • ' + x for x in s['weaknesses']]) if s['weaknesses'] else '  • No critical internal bottlenecks detected.'}

[*] OPPORTUNITIES:
{chr(10).join(['  • ' + x for x in s['opportunities']])}

[!] THREATS:
{chr(10).join(['  • ' + x for x in s['threats']]) if s['threats'] else '  • Exposure metrics within normal operational limits.'}

--------------------------------------------------------------------------------
3. SPECIALIST AGENT STRATEGIC RECOMMENDATIONS
--------------------------------------------------------------------------------
[Data Integrity & Quality Agent]
{chr(10).join(['• ' + x for x in q['recommendations']])}

[Key Driver & Performance Agent]
{chr(10).join(['• ' + x for x in d['recommendations']])}

[Dimensional & Segment Strategist]
{chr(10).join(['• ' + x for x in seg['recommendations']])}

{f"[Temporal & Trend Strategist]{chr(10)}" + chr(10).join(['• ' + x for x in t['recommendations']]) if t.get('has_temporal') else ''}

--------------------------------------------------------------------------------
4. PRIORITIZED STRATEGIC ROADMAP
--------------------------------------------------------------------------------
⚡ PHASE 1: IMMEDIATE INTERVENTIONS (Next 7 Days)
{chr(10).join(['  1.' + str(i+1) + ' ' + x for i, x in enumerate(r['phase_1_immediate_7_days'])])}

🎯 PHASE 2: TACTICAL OPTIMIZATION (Days 8 to 30)
{chr(10).join(['  2.' + str(i+1) + ' ' + x for i, x in enumerate(r['phase_2_tactical_30_days'])])}

🚀 PHASE 3: STRATEGIC GROWTH & SCALE (Days 31 to 90)
{chr(10).join(['  3.' + str(i+1) + ' ' + x for i, x in enumerate(r['phase_3_strategic_90_days'])])}
================================================================================
"""

