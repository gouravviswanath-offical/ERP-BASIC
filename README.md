# AI ERP Multi-Agent Strategic Intelligence System

An enterprise multi-agent ERP architecture that ingests business datasets from **Excel (`.xlsx`, `.xls`), CSV, and JSON**, scans operational performance across departments, and delivers **prioritized strategic business recommendations** (SWOT analysis, Business Health Score, 7/30/90-day action roadmaps, and working capital optimization).

---

## 🏗️ Architectural Overview & ERP Model Analysis

### 1. The Core ERP Model
The system is built on an SQLite transactional backbone with automatic schema normalization:
- **`products`**: Catalog with inventory counts, dynamic reorder thresholds, selling prices, unit costs, and categories.
- **`customers`**: Client directory with contact numbers, email, and historical billing links.
- **`invoices`**: Billing transactions tracking total amounts, paid portions, balances due, and timestamps.
- **`invoice_items`**: Granular line items linking orders to specific product units and historical rates.

### 2. Multi-Agent Strategic Architecture
Unlike simple transactional ERPs, this platform employs a collaborative **Multi-Agent System** where autonomous specialist agents audit distinct business vectors:

```
                          ┌────────────────────────┐
                          │   Chief Strategy       │
                          │   Officer (Executive)  │
                          └───────────┬────────────┘
                                      │
            ┌──────────────┬──────────┴───────────┬──────────────┐
            ▼              ▼                      ▼              ▼
     ┌─────────────┐ ┌─────────────┐       ┌─────────────┐ ┌─────────────┐
     │  Inventory  │ │    Sales    │       │   Finance   │ │  Customer   │
     │  Strategist │ │  Strategist │       │  Strategist │ │  Strategist │
     └──────┬──────┘ └──────┬──────┘       └──────┬──────┘ └──────┬──────┘
            │               │                     │               │
  • Safety Stock    • Pareto 80/20 Rule   • AR Debtor DSO • RFM Analysis
  • Dead Capital    • Basket AOV          • Cash Crunch   • Churn Alerts
  • ABC Class       • Margin Bundling     • 2/10 Net 30   • VIP Retention
```

- **📦 Inventory Strategist**: Analyzes stock-to-sales velocity, detects critical stockout risks, tags dormant/dead inventory holding capital captive, and computes ABC inventory classes.
- **📈 Sales Strategist**: Evaluates revenue velocity, customer revenue concentration risk (Pareto vulnerability), Average Order Value (AOV), and flagship product cross-selling.
- **💰 Finance Strategist**: Audits Accounts Receivable (AR), tracks collection efficiency, identifies high-exposure debtors, and recommends early-payment discounts and credit freeze policies.
- **👥 Customer Strategist**: Performs RFM (Recency, Frequency, Monetary) segmentation, spots churn signals before accounts lapse, and formulates VIP loyalty programs.
- **🏢 Chief Strategy Officer (CSO Agent)**: Synthesizes cross-agent telemetry into an overarching **Business Health Score (0-100)**, an algorithmic SWOT matrix, and a **3-tier actionable implementation plan** (Immediate 7-Day, Tactical 30-Day, Strategic 90-Day).

---

## 📥 Ingesting Your Data (Excel, CSV, ERP Exports)

You can import your own real-world data formatted as:
1. **Multi-Sheet Workbooks (`.xlsx`)**: With sheets named `Products`, `Customers`, `Invoices` / `ERP_Sales_Transactions`.
2. **Single Flat Transaction Exports (`.xlsx` or `.csv`)**: Exports from **Tally, Zoho Books, QuickBooks, Odoo, SAP, or custom spreadsheets** containing transaction rows:
   - *Columns supported (auto-detected via flexible synonyms):*
     - `Date` / `Created At`
     - `Invoice No` / `Bill No`
     - `Customer Name` / `Client` / `Party Name`
     - `Phone` / `Email`
     - `Product Name` / `Item Description`
     - `Category`
     - `Qty` / `Units Sold`
     - `Unit Price` / `Rate`
     - `Total Amount` / `Bill Amount`
     - `Paid Amount` / `Due Amount`
     - `Stock on Hand` / `Reorder Level`

### Generating a Pre-formatted Template
```bash
python ERP.py --template
```
This generates `sample_erp_data.xlsx` populated with realistic data that you can inspect, modify in Excel, and re-import!

---

## 🚀 How to Run the System

### 1. Interactive Command Line Hub (`ERP.py`)
Run the unified management hub:
```bash
python ERP.py
```
Or use direct CLI flags:
- Import Excel and scan immediately:
  ```bash
  python ERP.py --import-file sample_erp_data.xlsx --scan
  ```
- Run strategic scan on existing data:
  ```bash
  python ERP.py --scan
  ```
- Generate template:
  ```bash
  python ERP.py --template
  ```
- Launch Web Dashboard:
  ```bash
  python ERP.py --ui
  ```

### 2. Modern Interactive Web Dashboard (Streamlit)
Launch the rich browser GUI:
```bash
streamlit run app.py
```
**Features:**
- Drag-and-drop Excel or CSV upload with instant validation.
- Interactive KPI cards (Revenue, Dues, Stockout Alerts, Health Score).
- Dedicated tabs for Executive Roadmap, Inventory ABC Matrix, Sales Analytics, Finance Receivables, and Customer Health.
- Live Database Table Explorer.

### 3. Natural Language Chat Assistant (`main.py`)
Chat directly with specialist agents:
```bash
python main.py
```
**Example Prompts:**
- *"Scan our data and suggest strategies to improve the business"*
- *"Which products are low on stock and what are the reorder priorities?"*
- *"Who owes us money and which debtors are high risk?"*
- *"import sample_erp_data.xlsx"*
- *"status"*

---

## ⚙️ Configuration (Optional LLM Integration)
The system operates in **Dual-Engine Mode**:
1. **Deterministic Multi-Agent Engine**: Runs 100% locally and offline without requiring an API key. Computes exact ratios, ABC classes, debtor aging, Pareto concentration, and health scores mathematically.
2. **Generative LLM Engine (Groq / Llama 3.3)**: When a `GROQ_API_KEY` is placed in `.env`, the Executive Strategist synthesizes boardroom-level narrative commentary and supports conversational inquiries.

```bash
cp .env.example .env
# Set GROQ_API_KEY=your_key_here
```
