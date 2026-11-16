"""
AI ERP Core Hub
Provides full CLI and programmatic orchestration for:
1. Universal Ingestion of ANY dataset (Excel, CSV, JSON, Parquet)
2. Running the Universal Multi-Agent Business Strategy Scanner (Zero-Hallucination)
3. Generating customizable sample Excel templates
4. Natural language data query engine
5. Streamlit Dashboard launcher
"""
import sys
import os
import argparse
import pandas as pd
from db import init_db, get_conn
from data_importer import DataImporter, generate_sample_excel_template
from data_query_engine import get_active_dataframe, answer_data_query


def print_banner():
    banner = r"""
  ╔══════════════════════════════════════════════════════════════════════╗
  ║              AI ERP UNIVERSAL MULTI-AGENT INTELLIGENCE               ║
  ║        Self-Adapting Business Strategy Engine For ANY Dataset        ║
  ╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def show_database_summary():
    """Prints a high-level summary of active dataset and ERP database."""
    df = get_active_dataframe()
    con = get_conn()
    p_count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    c_count = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    i_count = con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    total_sales = con.execute("SELECT COALESCE(SUM(total), 0) FROM invoices").fetchone()[0]
    con.close()

    print("\n--- CURRENT DATASET & ERP STATUS ---")
    if len(df) > 0:
        print(f"• Active Dataset Rows : {len(df):,}")
        print(f"• Dataset Attributes  : {len(df.columns)} ({', '.join(list(df.columns)[:5])}...)")
    print(f"• Products in Catalog : {p_count}")
    print(f"• Customer Accounts   : {c_count}")
    print(f"• Invoices Processed  : {i_count}")
    print(f"• Total Sales Volume  : Rs. {total_sales:,.2f}")
    print("------------------------------------\n")


def run_strategy_scan():
    """Executes the self-tuning multi-agent scan across all dimensions."""
    df = get_active_dataframe()
    if len(df) > 0:
        print("\n[Universal Multi-Agent System] Initializing self-tuning specialist agents...")
        print(f"   -> Analyzing Dataset: {len(df):,} records across {len(df.columns)} columns")
        print("   -> [Data Quality Agent] Auditing types, completeness & zero-value anomalies...")
        print("   -> [Key Driver Agent] Discovering primary metric & Pareto 80/20 distribution...")
        print("   -> [Segment Strategist] Cross-tabulating categorical dimensions & upside...")
        print("   -> [Temporal Strategist] Analyzing growth trajectory & seasonality...")
        print("   -> [Chief Strategy Officer] Synthesizing data-grounded SWOT & 3-tier roadmap...\n")

        from universal_agents import UniversalChiefStrategyOfficer
        cso = UniversalChiefStrategyOfficer(df, dataset_name="Active Dataset")
        dossier = cso.run_universal_scan()
        narrative = cso.generate_executive_narrative(dossier)
        print(narrative)
        return dossier
    else:
        from strategy_agents import ExecutiveStrategistAgent
        cso = ExecutiveStrategistAgent()
        dossier = cso.run_comprehensive_scan()
        narrative = cso.generate_ai_narrative(dossier)
        print(narrative)
        return dossier


def handle_import(file_path: str, clear_existing: bool = False):
    """Imports an Excel or CSV file into the universal engine."""
    print(f"\n[Universal Importer] Profiling and ingesting '{file_path}'...")
    importer = DataImporter()
    stats = importer.import_file(file_path, clear_existing=clear_existing)
    print(f"\n[Universal Importer] SUCCESS: Ingested dataset:")
    print(f"   • Total records loaded    : {stats.get('raw_total_rows', 0):,}")
    print(f"   • Columns discovered      : {stats.get('raw_total_columns', 0)}")
    print(f"   • Primary metric found    : '{stats.get('primary_metric', 'N/A')}'")
    print(f"   • Data quality score      : {stats.get('data_quality_score', 0)}/100")
    print(f"   • Key dimensions mapped   : {', '.join(stats.get('dimensions_found', []))}")
    show_database_summary()


def handle_template(output_path: str = "sample_erp_data.xlsx"):
    """Generates a sample Excel template."""
    print(f"\n[Template Generator] Creating sample dataset at '{output_path}'...")
    generate_sample_excel_template(output_path)
    print(f"[Template Generator] Template successfully generated: '{output_path}'.")


def launch_ui():
    """Launches the Streamlit Web Application."""
    print("\n[UI Launcher] Launching Universal Streamlit Dashboard...")
    os.system("streamlit run app.py")


def interactive_menu():
    init_db()
    print_banner()
    show_database_summary()

    while True:
        print("\nSelect an option:")
        print("1. [Scan] Run Universal Multi-Agent Business Strategy Scan")
        print("2. [Import] Ingest ANY Dataset (Excel, CSV, JSON, Parquet)")
        print("3. [Ask] Query Loaded Dataset (Exact numbers, zero hallucinations)")
        print("4. [Dashboard] Launch Interactive Web Dashboard (Streamlit)")
        print("5. [Template] Generate Sample Excel Dataset")
        print("6. [Status] View Current Dataset Status")
        print("7. [Exit] Quit")

        choice = input("\nEnter choice (1-7): ").strip()

        if choice == "1":
            run_strategy_scan()
        elif choice == "2":
            path = input("Enter path to file (or press Enter for 'sample_erp_data.xlsx'): ").strip()
            if not path:
                path = "sample_erp_data.xlsx"
                if not os.path.exists(path):
                    handle_template(path)
            if not os.path.exists(path):
                print(f"Error: File '{path}' not found.")
                continue
            try:
                handle_import(path, clear_existing=False)
            except Exception as e:
                print(f"Error importing file: {e}")
        elif choice == "3":
            q = input("Ask a question about your data (e.g., 'total sales', 'top 5 products', 'average price'): ").strip()
            if q:
                ans = answer_data_query(q)
                print(f"\nAnswer:\n{ans}\n")
        elif choice == "4":
            launch_ui()
            break
        elif choice == "5":
            out = input("Enter output filename (default: sample_erp_data.xlsx): ").strip() or "sample_erp_data.xlsx"
            handle_template(out)
        elif choice == "6":
            show_database_summary()
        elif choice in ("7", "exit", "quit", "q"):
            print("\nExiting AI ERP. Have a great day!")
            break
        else:
            print("Invalid option. Please choose between 1 and 7.")


def main():
    parser = argparse.ArgumentParser(description="AI ERP Universal Multi-Agent Strategy System")
    parser.add_argument("--import-file", "-i", dest="import_file", help="Path to any dataset file to import")
    parser.add_argument("--clear", action="store_true", help="Clear existing DB before importing")
    parser.add_argument("--scan", "-s", action="store_true", help="Run universal multi-agent strategy scan")
    parser.add_argument("--query", "-q", dest="query", help="Ask a question about the active dataset")
    parser.add_argument("--template", "-t", action="store_true", help="Generate sample Excel dataset")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit Web UI")
    parser.add_argument("--summary", action="store_true", help="Show summary")

    args = parser.parse_args()

    init_db()

    if args.template:
        handle_template("sample_erp_data.xlsx")
        return

    if args.import_file:
        handle_import(args.import_file, clear_existing=args.clear)
        if args.scan:
            run_strategy_scan()
        return

    if args.scan:
        run_strategy_scan()
        return

    if args.query:
        ans = answer_data_query(args.query)
        print(f"\nAnswer:\n{ans}\n")
        return

    if args.ui:
        launch_ui()
        return

    if args.summary:
        show_database_summary()
        return

    interactive_menu()


if __name__ == "__main__":
    main()
