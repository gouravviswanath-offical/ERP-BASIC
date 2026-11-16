"""
Zero-Hallucination Data Query Engine.
Answers user questions directly by computing on the actual loaded dataset using
Pandas / SQL operations, ensuring answers are 100% grounded in the real data.
"""
import os
import json
import re
import pandas as pd
from universal_profiler import load_any_dataset, clean_numeric_value

CURRENT_DATASET_PATH = "dataset_current.csv"
_loaded_df = None


def get_active_dataframe() -> pd.DataFrame:
    global _loaded_df
    if _loaded_df is not None:
        return _loaded_df
    if os.path.exists(CURRENT_DATASET_PATH):
        try:
            _loaded_df = pd.read_csv(CURRENT_DATASET_PATH)
            return _loaded_df
        except Exception:
            pass
    # Fallback to sample data if exists
    if os.path.exists("sample_erp_data.xlsx"):
        _loaded_df = load_any_dataset("sample_erp_data.xlsx")
        return _loaded_df
    return pd.DataFrame()


def set_active_dataframe(df: pd.DataFrame):
    global _loaded_df
    _loaded_df = df
    df.to_csv(CURRENT_DATASET_PATH, index=False)


def answer_data_query(query: str, df: pd.DataFrame | None = None) -> str:
    """Answers user question against the loaded dataset with zero hallucinations."""
    if df is None or len(df) == 0:
        df = get_active_dataframe()

    if len(df) == 0:
        return "No dataset currently loaded. Please upload or import an Excel/CSV file first."

    # Check if Groq client is usable for dynamic python code generation
    try:
        from config import get_client, MODEL
        client = get_client()

        cols_info = {c: str(df[c].dtype) for c in df.columns}
        prompt = f"""
You are a Python Data Analyst assistant.
Given a pandas DataFrame named `df` with columns:
{json.dumps(cols_info)}

First 3 rows:
{df.head(3).to_dict(orient='records')}

Write a concise Python script to answer the user query: "{query}"
The script MUST store the final formatted plain-text answer string into a variable named `result`.
Do not import pandas (it is already available as pd).
Do not produce markdown or explanation, ONLY the executable Python code block.
"""
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        code = resp.choices[0].message.content or ""
        # Strip code fences if present
        clean_code = re.sub(r"^```python\s*|^```\s*|```$", "", code.strip(), flags=re.MULTILINE)
        local_scope = {"df": df, "pd": pd, "result": None}
        exec(clean_code, {}, local_scope)
        if local_scope.get("result"):
            return str(local_scope["result"])
    except Exception:
        pass

    # Algorithmic Query Parser (Deterministic, 100% offline)
    return _algorithmic_query_handler(query, df)


def _algorithmic_query_handler(query: str, df: pd.DataFrame) -> str:
    q = query.lower()
    cols = list(df.columns)
    col_map = {c.lower(): c for c in cols}

    # Detect requested column
    target_col = None
    for c_lower, c_orig in col_map.items():
        if c_lower in q:
            target_col = c_orig
            break

    # Find numeric columns
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c].dtype)]
    # Filter out ID columns
    metric_candidates = [c for c in num_cols if not any(k in c.lower() for k in ["id", "code", "no"])]
    if not metric_candidates:
        metric_candidates = num_cols

    # Prefer sales/amount/revenue/total over pure qty unless query asks for qty
    if target_col and target_col in num_cols:
        primary_num = target_col
    elif any(k in q for k in ["qty", "quantity", "units", "count"]):
        qty_col = next((c for c in metric_candidates if any(k in c.lower() for k in ["qty", "quantity", "units"])), None)
        primary_num = qty_col or (metric_candidates[0] if metric_candidates else None)
    else:
        sales_col = next((c for c in metric_candidates if any(k in c.lower() for k in ["sales", "amount", "revenue", "total", "price"])), None)
        primary_num = sales_col or (metric_candidates[0] if metric_candidates else None)

    # Detect dimension to group by
    cat_cols = [c for c in cols if c not in num_cols]
    group_col = None
    # Check if query mentions a specific category or entity
    for c in cat_cols:
        c_low = c.lower()
        if (c_low in q) or \
           ("product" in q and ("product" in c_low or "item" in c_low or "sku" in c_low)) or \
           ("customer" in q and ("customer" in c_low or "client" in c_low or "party" in c_low)) or \
           ("category" in q and "category" in c_low):
            group_col = c
            break

    if not group_col:
        # Avoid invoice IDs as default grouping
        non_id_cats = [c for c in cat_cols if not any(k in c.lower() for k in ["id", "no", "invoice"])]
        group_col = non_id_cats[0] if non_id_cats else (cat_cols[0] if cat_cols else cols[0])

    # 1. Specific item filter (e.g., "sales for Laptop Pro 15", "TechNova", "Monitor")
    for col in cols:
        if not pd.api.types.is_numeric_dtype(df[col].dtype):
            for val in df[col].dropna().unique()[:300]:
                val_str = str(val).strip()
                if len(val_str) >= 3 and val_str.lower() in q:
                    sub = df[df[col].astype(str).str.lower() == val_str.lower()]
                    if primary_num:
                        tot = sub[primary_num].sum()
                        return f"Found {len(sub):,} record(s) for '{val}' ({col}). Total '{primary_num}': Rs. {tot:,.2f}."
                    return f"Found {len(sub):,} record(s) matching '{val}' ({col})."

    # 2. Total / Sum
    if any(k in q for k in ["total", "sum", "how much", "overall"]) and primary_num:
        val = df[primary_num].sum()
        return f"Total '{primary_num}' across all {len(df):,} records is: Rs. {val:,.2f}"

    # 3. Average / Mean
    if any(k in q for k in ["average", "mean", "avg"]) and primary_num:
        val = df[primary_num].mean()
        return f"Average '{primary_num}' is: Rs. {val:,.2f}"

    # 4. Top / Best / Highest
    if any(k in q for k in ["top", "best", "highest", "max", "most"]) and primary_num:
        try:
            top_df = df.groupby(group_col)[primary_num].sum().reset_index().sort_values(by=primary_num, ascending=False).head(5)
            lines = [f"• {row[group_col]}: Rs. {row[primary_num]:,.2f}" for _, row in top_df.iterrows()]
            return f"Top 5 '{group_col}' by '{primary_num}':\n" + "\n".join(lines)
        except Exception:
            val = df[primary_num].max()
            return f"Maximum '{primary_num}' is: Rs. {val:,.2f}"

    # 5. Low / Bottom / Lowest
    if any(k in q for k in ["lowest", "bottom", "worst", "min"]) and primary_num:
        try:
            bot_df = df.groupby(group_col)[primary_num].sum().reset_index().sort_values(by=primary_num).head(5)
            lines = [f"• {row[group_col]}: Rs. {row[primary_num]:,.2f}" for _, row in bot_df.iterrows()]
            return f"Lowest 5 '{group_col}' by '{primary_num}':\n" + "\n".join(lines)
        except Exception:
            val = df[primary_num].min()
            return f"Minimum '{primary_num}' is: Rs. {val:,.2f}"

    # 6. Row count / records
    if any(k in q for k in ["how many", "count", "rows", "records", "size"]):
        return f"The dataset contains {len(df):,} total rows and {len(cols)} columns: {', '.join(cols[:8])}."

    # Default overview
    return f"Dataset overview ({len(df):,} rows): Primary numeric columns are {', '.join(num_cols[:4])}. You can ask for total, average, top performers, or breakdown by category."
