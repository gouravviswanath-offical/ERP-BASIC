"""
Multi-Agent Strategic Intelligence Engine for AI ERP.
Specialized Strategic Agents:
1. InventoryStrategist: Supply chain resilience, ABC categorization, dead stock liquidation, replenishment.
2. SalesStrategist: Revenue optimization, customer concentration (Pareto), product mix matrix, bundling.
3. FinanceStrategist: Working capital, debtor aging, collection efficiency, cash flow risks.
4. CustomerStrategist: RFM segmentation, churn warning, loyalty & retention strategy.
5. ExecutiveStrategist (CSO): Consolidates multi-agent intelligence into Business Health Score (0-100),
   SWOT analysis, and 7/30/90-day prioritized strategic roadmap.
"""
import os
import json
from datetime import datetime, timedelta
from db import get_conn


class InventoryStrategistAgent:
    name = "Inventory Strategist"
    role = "Supply Chain & Working Capital Optimization"

    def scan(self) -> dict:
        con = get_conn()
        products = [dict(r) for r in con.execute("SELECT * FROM products").fetchall()]
        
        # Calculate recent sales velocity per product (last 60 days)
        sixty_days_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        sales_data = {
            r["product_id"]: dict(r)
            for r in con.execute(
                """
                SELECT product_id, SUM(qty) as units_sold, SUM(qty * price) as revenue
                FROM invoice_items ii
                JOIN invoices i ON i.id = ii.invoice_id
                WHERE i.created_at >= ?
                GROUP BY product_id
                """,
                (sixty_days_ago,),
            ).fetchall()
        }
        con.close()

        total_inventory_value = 0.0
        stockout_items = []
        low_stock_items = []
        overstocked_items = []
        dead_stock_items = []
        all_prods_analyzed = []

        total_rev_all = sum(s.get("revenue", 0.0) for s in sales_data.values())

        for p in products:
            p_id = p["id"]
            name = p["name"]
            stock = p.get("stock", 0) or 0
            reorder = p.get("reorder_level", 10) or 10
            price = p.get("price", 0.0) or 0.0
            cost = p.get("cost", price * 0.7) or (price * 0.7)
            
            val = stock * price
            total_inventory_value += val
            s_info = sales_data.get(p_id, {"units_sold": 0, "revenue": 0.0})
            units_sold = s_info["units_sold"]
            rev = s_info["revenue"]

            item_summary = {
                "id": p_id,
                "name": name,
                "stock": stock,
                "reorder_level": reorder,
                "price": price,
                "cost": cost,
                "inventory_value": val,
                "units_sold_60d": units_sold,
                "revenue_60d": rev,
            }
            all_prods_analyzed.append(item_summary)

            if stock == 0:
                stockout_items.append(item_summary)
            elif stock < reorder:
                low_stock_items.append(item_summary)
            elif stock > (reorder * 3) and units_sold == 0:
                dead_stock_items.append(item_summary)
            elif stock > (reorder * 2.5) and units_sold < (stock * 0.1):
                overstocked_items.append(item_summary)

        # ABC Analysis (Rank products by revenue contribution)
        sorted_by_rev = sorted(all_prods_analyzed, key=lambda x: x["revenue_60d"], reverse=True)
        running_rev = 0.0
        for item in sorted_by_rev:
            running_rev += item["revenue_60d"]
            pct = (running_rev / total_rev_all * 100) if total_rev_all > 0 else 0
            if pct <= 75:
                item["abc_class"] = "A (High Impact)"
            elif pct <= 95:
                item["abc_class"] = "B (Moderate)"
            else:
                item["abc_class"] = "C (Low Impact)"

        dead_capital = sum(item["inventory_value"] for item in dead_stock_items)

        # Formulate Strategic Recommendations
        recommendations = []
        if stockout_items:
            names = ", ".join([x["name"] for x in stockout_items[:3]])
            recommendations.append(f"CRITICAL REORDER: Immediate supply order required for stockout items: {names}. Lost sales occurring daily.")
        if low_stock_items:
            names = ", ".join([f"{x['name']} (Stock: {x['stock']}, Min: {x['reorder_level']})" for x in low_stock_items[:3]])
            recommendations.append(f"PREVENTIVE REPLENISHMENT: {len(low_stock_items)} items are below safety threshold: {names}. Issue POs within 48 hours.")
        if dead_stock_items:
            recommendations.append(f"WORKING CAPITAL RELEASE: Rs. {dead_capital:,.2f} is frozen in dead/slow inventory. Launch a 15-25% clearance or bundle discount with Class A items to recoup cash.")
        if not recommendations:
            recommendations.append("Inventory levels are currently well balanced within reorder thresholds.")

        return {
            "total_skus": len(products),
            "total_inventory_value": total_inventory_value,
            "dead_capital_locked": dead_capital,
            "stockout_count": len(stockout_items),
            "low_stock_count": len(low_stock_items),
            "dead_stock_count": len(dead_stock_items),
            "stockout_items": stockout_items,
            "low_stock_items": low_stock_items,
            "dead_stock_items": dead_stock_items,
            "abc_items": sorted_by_rev,
            "recommendations": recommendations,
        }


class SalesStrategistAgent:
    name = "Sales Strategist"
    role = "Revenue Acceleration & Margin Maximization"

    def scan(self) -> dict:
        con = get_conn()
        invoices = [dict(r) for r in con.execute("SELECT * FROM invoices").fetchall()]
        cust_sales = [dict(r) for r in con.execute(
            """
            SELECT c.name as customer, SUM(i.total) as total_spent, COUNT(i.id) as order_count
            FROM invoices i JOIN customers c ON c.id = i.customer_id
            GROUP BY c.id ORDER BY total_spent DESC
            """
        ).fetchall()]
        top_prods = [dict(r) for r in con.execute(
            """
            SELECT p.name, SUM(ii.qty) as total_qty, SUM(ii.qty * ii.price) as revenue
            FROM invoice_items ii
            JOIN products p ON p.id = ii.product_id
            GROUP BY p.id ORDER BY revenue DESC
            """
        ).fetchall()]
        con.close()

        total_revenue = sum(inv["total"] for inv in invoices)
        total_orders = len(invoices)
        aov = (total_revenue / total_orders) if total_orders > 0 else 0.0

        # Customer Concentration (Pareto Risk)
        concentration_risk = "Low"
        top_customer_pct = 0.0
        if cust_sales and total_revenue > 0:
            top_customer_spend = cust_sales[0]["total_spent"]
            top_customer_pct = round((top_customer_spend / total_revenue) * 100, 1)
            if top_customer_pct >= 50:
                concentration_risk = "Critical (High Vulnerability)"
            elif top_customer_pct >= 35:
                concentration_risk = "Moderate"

        recommendations = []
        if top_customer_pct >= 35 and cust_sales:
            recommendations.append(
                f"CLIENT DIVERSIFICATION: Top client '{cust_sales[0]['customer']}' generates {top_customer_pct}% of total revenue. "
                "Aggressively prospect 3-5 new enterprise accounts to protect against single-customer churn risk."
            )
        if aov > 0:
            recommendations.append(
                f"BASKET SIZE EXPANSION: Current Average Order Value (AOV) is Rs. {aov:,.2f}. Implement minimum order incentives "
                f"or bundle deals to push target AOV towards Rs. {aov * 1.25:,.2f}."
            )
        if top_prods:
            star = top_prods[0]
            recommendations.append(
                f"FLAGSHIP MONETIZATION: '{star['name']}' is your top revenue driver (Rs. {star['revenue']:,.2f}). "
                "Protect supplier pipeline, guarantee delivery SLAs, and pair slow-moving accessories with this item."
            )

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "average_order_value": aov,
            "concentration_risk": concentration_risk,
            "top_customer_share_pct": top_customer_pct,
            "customer_sales_breakdown": cust_sales,
            "top_products": top_prods,
            "recommendations": recommendations,
        }


class FinanceStrategistAgent:
    name = "Finance Strategist"
    role = "Cash Flow Protection & Working Capital Health"

    def scan(self) -> dict:
        con = get_conn()
        invoices = [dict(r) for r in con.execute("SELECT * FROM invoices").fetchall()]
        dues = [dict(r) for r in con.execute(
            """
            SELECT c.name as customer, c.phone, SUM(i.total) as billed, SUM(i.paid) as paid,
                   SUM(i.total - i.paid) as due, COUNT(i.id) as invoice_count
            FROM invoices i JOIN customers c ON c.id = i.customer_id
            GROUP BY c.id HAVING due > 0 ORDER BY due DESC
            """
        ).fetchall()]
        con.close()

        total_billed = sum(inv["total"] for inv in invoices)
        total_paid = sum(inv["paid"] for inv in invoices)
        total_outstanding = sum(inv["total"] - inv["paid"] for inv in invoices)

        collection_rate = (total_paid / total_billed * 100) if total_billed > 0 else 100.0

        # Debtor Aging & Concentration Risk
        top_debtor = dues[0] if dues else None
        debtor_concentration = 0.0
        if top_debtor and total_outstanding > 0:
            debtor_concentration = round((top_debtor["due"] / total_outstanding) * 100, 1)

        recommendations = []
        if total_outstanding > 0:
            recommendations.append(
                f"COLLECTION ACCELERATION: Rs. {total_outstanding:,.2f} is currently locked in accounts receivable (Collection Rate: {collection_rate:.1f}%)."
            )
        if top_debtor and debtor_concentration >= 40:
            recommendations.append(
                f"CREDIT STOP RISK: '{top_debtor['customer']}' owes Rs. {top_debtor['due']:,.2f} ({debtor_concentration}% of all outstanding debt). "
                "Enforce a temporary credit freeze on new shipments until past dues are cleared to 50%."
            )
        recommendations.append(
            "TERMS RESTRUCTURING: Introduce a '2/10 Net 30' cash discount policy (2% discount for payment within 10 days) to accelerate incoming cash flow."
        )

        return {
            "total_billed": total_billed,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "collection_rate_pct": collection_rate,
            "debtor_count": len(dues),
            "debtors": dues,
            "top_debtor": top_debtor,
            "top_debtor_share_pct": debtor_concentration,
            "recommendations": recommendations,
        }


class CustomerStrategistAgent:
    name = "Customer Strategist"
    role = "Client Retention & Account Health"

    def scan(self) -> dict:
        con = get_conn()
        cust_records = [dict(r) for r in con.execute(
            """
            SELECT c.id, c.name, c.phone,
                   COUNT(i.id) as total_invoices,
                   COALESCE(SUM(i.total), 0) as total_spent,
                   MAX(i.created_at) as last_order_date
            FROM customers c
            LEFT JOIN invoices i ON i.customer_id = c.id
            GROUP BY c.id
            """
        ).fetchall()]
        con.close()

        now = datetime.now()
        segmented = []
        churn_risk_count = 0
        vip_count = 0

        for c in cust_records:
            last_date_str = c.get("last_order_date")
            days_since = 999
            if last_date_str:
                try:
                    last_dt = datetime.strptime(str(last_date_str)[:19], "%Y-%m-%d %H:%M:%S")
                    days_since = (now - last_dt).days
                except Exception:
                    try:
                        last_dt = datetime.strptime(str(last_date_str)[:10], "%Y-%m-%d")
                        days_since = (now - last_dt).days
                    except Exception:
                        days_since = 30

            spent = c["total_spent"]
            inv_count = c["total_invoices"]

            if inv_count >= 3 or spent >= 25000:
                tier = "VIP / Champion"
                vip_count += 1
            elif days_since > 30 and spent > 5000:
                tier = "At-Risk (Slipping)"
                churn_risk_count += 1
            elif inv_count == 1:
                tier = "One-Time Buyer"
            else:
                tier = "Active Regular"

            c["days_since_last_order"] = days_since
            c["segment"] = tier
            segmented.append(c)

        recommendations = []
        if churn_risk_count > 0:
            recommendations.append(
                f"WIN-BACK CAMPAIGN: {churn_risk_count} valuable client(s) haven't purchased in over 30 days. Dispatch relationship managers or personalized price incentives immediately."
            )
        if vip_count > 0:
            recommendations.append(
                f"VIP RETENTION: Protect {vip_count} key accounts with dedicated account executives, priority fulfillment, and volume quarterly rebate tiers."
            )
        recommendations.append(
            "SECOND ORDER CONVERSION: Automate follow-ups for one-time buyers 14 days post-purchase with complementary catalog offerings."
        )

        return {
            "total_customers": len(cust_records),
            "vip_count": vip_count,
            "churn_risk_count": churn_risk_count,
            "customer_segments": segmented,
            "recommendations": recommendations,
        }


class ExecutiveStrategistAgent:
    name = "Chief Strategy Officer"
    role = "Consolidated Business Intelligence & Strategic Roadmap"

    def __init__(self):
        self.inventory_agent = InventoryStrategistAgent()
        self.sales_agent = SalesStrategistAgent()
        self.finance_agent = FinanceStrategistAgent()
        self.customer_agent = CustomerStrategistAgent()

    def run_comprehensive_scan(self) -> dict:
        """Runs all multi-agent scans in parallel and synthesizes executive decisions."""
        inv_report = self.inventory_agent.scan()
        sales_report = self.sales_agent.scan()
        fin_report = self.finance_agent.scan()
        cust_report = self.customer_agent.scan()

        # Calculate Unified Business Health Index (0 to 100)
        # 1. Financial score (collection rate)
        fin_score = min(100.0, max(0.0, fin_report["collection_rate_pct"]))
        # 2. Inventory score (penalize stockouts and dead capital)
        skus = max(1, inv_report["total_skus"])
        stockout_penalty = (inv_report["stockout_count"] / skus) * 40
        dead_penalty = (inv_report["dead_stock_count"] / skus) * 30
        inv_score = max(0.0, 100.0 - stockout_penalty - dead_penalty)
        # 3. Sales & Customer score
        conc_penalty = 25.0 if sales_report["concentration_risk"] == "Critical (High Vulnerability)" else (10.0 if sales_report["concentration_risk"] == "Moderate" else 0.0)
        churn_penalty = min(30.0, cust_report["churn_risk_count"] * 10)
        cust_score = max(0.0, 100.0 - conc_penalty - churn_penalty)

        overall_health = round((fin_score * 0.35) + (inv_score * 0.35) + (cust_score * 0.30), 1)

        # SWOT Matrix Analysis
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        if fin_report["collection_rate_pct"] >= 70:
            strengths.append(f"Strong cash collection discipline ({fin_report['collection_rate_pct']:.1f}% collected).")
        else:
            weaknesses.append(f"High cash drag: Rs. {fin_report['total_outstanding']:,.2f} pending collection.")

        if sales_report["total_revenue"] > 0:
            strengths.append(f"Established revenue base of Rs. {sales_report['total_revenue']:,.2f} across {sales_report['total_orders']} orders.")

        if inv_report["stockout_count"] > 0:
            weaknesses.append(f"{inv_report['stockout_count']} high-demand items are completely out of stock.")
        if inv_report["dead_capital_locked"] > 0:
            weaknesses.append(f"Rs. {inv_report['dead_capital_locked']:,.2f} frozen in non-moving stock.")

        if inv_report["dead_capital_locked"] > 0:
            opportunities.append("Liquidate dead stock through clearance bundles to release quick operating cash.")
        opportunities.append("Restructure credit terms with 2/10 Net 30 discounts to accelerate receivables cycle.")
        opportunities.append(f"Cross-sell catalog products to increase Average Order Value beyond Rs. {sales_report['average_order_value']:,.2f}.")

        if sales_report["concentration_risk"] != "Low":
            threats.append(f"Severe customer concentration: single customer accounts for {sales_report['top_customer_share_pct']}% of revenue.")
        if fin_report["top_debtor"] and fin_report["top_debtor_share_pct"] >= 40:
            threats.append(f"Credit default exposure: '{fin_report['top_debtor']['customer']}' holds {fin_report['top_debtor_share_pct']}% of all unpaid dues.")

        # 3-Phase Prioritized Strategic Action Plan
        phase_1_immediate = []  # Next 7 Days
        phase_2_tactical = []   # Days 8 - 30
        phase_3_strategic = []  # Days 31 - 90

        # Phase 1
        if inv_report["stockout_items"]:
            phase_1_immediate.append(f"Issue emergency replenishment orders for stockout items ({', '.join([x['name'] for x in inv_report['stockout_items'][:2]])}).")
        if fin_report["top_debtor"]:
            phase_1_immediate.append(f"Execute debt collection outreach to '{fin_report['top_debtor']['customer']}' (Rs. {fin_report['top_debtor']['due']:,.2f} due).")
        if not phase_1_immediate:
            phase_1_immediate.append("Audit all upcoming invoice payment schedules for the current week.")

        # Phase 2
        if inv_report["dead_stock_items"]:
            phase_2_tactical.append(f"Launch promotional bundle campaign to liquidate Rs. {inv_report['dead_capital_locked']:,.2f} in stagnant inventory.")
        phase_2_tactical.append("Implement revised credit control policy (credit limits per customer tier and 2% early-pay discount).")
        if cust_report["churn_risk_count"] > 0:
            phase_2_tactical.append(f"Execute win-back campaign for {cust_report['churn_risk_count']} slipping customer accounts.")

        # Phase 3
        phase_3_strategic.append("Broaden client acquisition pipeline to reduce customer revenue concentration.")
        phase_3_strategic.append("Establish automated vendor reorder points (min-max inventory system) for Class A products.")
        phase_3_strategic.append("Establish quarterly executive business reviews (QBR) with top VIP accounts.")

        # Total Estimated Cash Realization Opportunity
        estimated_cash_potential = fin_report["total_outstanding"] + (inv_report["dead_capital_locked"] * 0.8)

        full_dossier = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "business_health_score": overall_health,
            "estimated_cash_opportunity": estimated_cash_potential,
            "inventory": inv_report,
            "sales": sales_report,
            "finance": fin_report,
            "customer": cust_report,
            "swot": {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "opportunities": opportunities,
                "threats": threats,
            },
            "strategic_roadmap": {
                "phase_1_immediate_7_days": phase_1_immediate,
                "phase_2_tactical_30_days": phase_2_tactical,
                "phase_3_strategic_90_days": phase_3_strategic,
            },
        }

        return full_dossier

    def generate_ai_narrative(self, dossier: dict) -> str:
        """
        If GROQ_API_KEY is available, uses the LLM to write a high-level executive strategic summary.
        Otherwise, returns a beautifully formatted algorithmic C-Suite Briefing.
        """
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
You are the Chief Strategy Officer of an AI-powered Enterprise ERP.
Analyze the following multi-agent business diagnostic scan and provide an incisive, boardroom-grade
Executive Strategic Assessment. Structure your response with:
1. Executive Briefing & Health Score Rating ({dossier['business_health_score']}/100)
2. Critical Bottlenecks & Operational Vulnerabilities
3. Multi-Agent Synthesis (Inventory, Sales, Finance, Customers)
4. Strategic Action Directives (7-day, 30-day, 90-day execution)
5. Projected Financial Realization (Releasing Rs. {dossier['estimated_cash_opportunity']:,.2f} in working capital)

Data Dossier:
{json.dumps(dossier, indent=2, default=str)}
"""
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                # Fall back to structured report
                pass

        # High quality algorithmic formatting
        return self._format_algorithmic_narrative(dossier)

    def _format_algorithmic_narrative(self, d: dict) -> str:
        s = d["swot"]
        r = d["strategic_roadmap"]
        fin = d["finance"]
        inv = d["inventory"]
        sales = d["sales"]
        cust = d["customer"]

        return f"""
================================================================================
                    EXECUTIVE STRATEGIC BUSINESS ASSESSMENT
================================================================================
Scan Timestamp: {d['timestamp']}
Overall Business Health Score: {d['business_health_score']} / 100
Working Capital Release Opportunity: Rs. {d['estimated_cash_opportunity']:,.2f}

--------------------------------------------------------------------------------
1. EXECUTIVE DIAGNOSTIC SUMMARY
--------------------------------------------------------------------------------
• Health Rating: {'HEALTHY' if d['business_health_score'] >= 75 else ('MODERATE ATTENTION REQUIRED' if d['business_health_score'] >= 50 else 'HIGH OPERATIONAL RISK')}
• Financial Exposure: Rs. {fin['total_outstanding']:,.2f} pending collection ({fin['collection_rate_pct']:.1f}% collection rate across {fin['debtor_count']} debtors).
• Inventory Balance: Rs. {inv['total_inventory_value']:,.2f} total stock value. {inv['stockout_count']} stockouts, {inv['low_stock_count']} low-stock items, Rs. {inv['dead_capital_locked']:,.2f} in dead inventory.
• Commercial Performance: Rs. {sales['total_revenue']:,.2f} revenue across {sales['total_orders']} orders (AOV: Rs. {sales['average_order_value']:,.2f}).
• Concentration Risk: {sales['concentration_risk']} (Top customer represents {sales['top_customer_share_pct']}% of revenue).

--------------------------------------------------------------------------------
2. SWOT STRATEGIC MATRIX
--------------------------------------------------------------------------------
[+] STRENGTHS:
{chr(10).join(['  • ' + x for x in s['strengths']]) if s['strengths'] else '  • Baseline trading operations active.'}

[-] WEAKNESSES:
{chr(10).join(['  • ' + x for x in s['weaknesses']]) if s['weaknesses'] else '  • No critical internal bottlenecks detected.'}

[*] OPPORTUNITIES:
{chr(10).join(['  • ' + x for x in s['opportunities']])}

[!] THREATS:
{chr(10).join(['  • ' + x for x in s['threats']]) if s['threats'] else '  • Market exposure within normal tolerances.'}

--------------------------------------------------------------------------------
3. MULTI-AGENT DOMAIN RECOMMENDATIONS
--------------------------------------------------------------------------------
[Inventory Strategist]
{chr(10).join(['• ' + x for x in inv['recommendations']])}

[Sales Strategist]
{chr(10).join(['• ' + x for x in sales['recommendations']])}

[Finance Strategist]
{chr(10).join(['• ' + x for x in fin['recommendations']])}

[Customer Strategist]
{chr(10).join(['• ' + x for x in cust['recommendations']])}

--------------------------------------------------------------------------------
4. PRIORITIZED STRATEGIC EXECUTION ROADMAP
--------------------------------------------------------------------------------
⚡ PHASE 1: IMMEDIATE INTERVENTIONS (Next 7 Days)
{chr(10).join(['  1.' + str(i+1) + ' ' + x for i, x in enumerate(r['phase_1_immediate_7_days'])])}

🎯 PHASE 2: TACTICAL OPTIMIZATION (Days 8 to 30)
{chr(10).join(['  2.' + str(i+1) + ' ' + x for i, x in enumerate(r['phase_2_tactical_30_days'])])}

🚀 PHASE 3: STRATEGIC GROWTH & SCALE (Days 31 to 90)
{chr(10).join(['  3.' + str(i+1) + ' ' + x for i, x in enumerate(r['phase_3_strategic_90_days'])])}
================================================================================
"""

