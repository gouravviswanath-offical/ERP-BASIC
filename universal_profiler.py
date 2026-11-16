"""
Universal Data Profiler & Semantic Auto-Discovery Engine.
Ingests ANY tabular dataset (Excel, CSV, JSON, Parquet) regardless of domain (Sales, HR,
Operations, Logistics, Finance, SaaS, Healthcare) and automatically:
1. Cleans formatted numbers, currencies, dates, and missing values.
2. Infers data types and semantic roles (Primary Metric, Dimensions, Temporal, Target Label, IDs).
3. Computes statistical distributions, correlations, outliers, and class distributions.
4. Generates a structured mathematical profile that multi-agent systems use for zero-hallucination analysis.
"""
import os
import re
import json
import warnings
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning)


def clean_numeric_value(val, default=0.0):
    """Safely parses currency, percentages, commas, and formatted numbers into floats."""
    if val is None or pd.isna(val):
        return default
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val) if not np.isnan(val) else default
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "-", "n/a", ""):
        return default
    # Remove currency symbols, commas, spaces, quotes, percent
    s_clean = re.sub(r"[^\d\.\-+eE]", "", s)
    try:
        return float(s_clean)
    except Exception:
        return default


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans column names and cleans text/numeric/date fields."""
    df_clean = df.copy()
    # Strip whitespace from column headers
    df_clean.columns = [str(c).strip() for c in df_clean.columns]

    for col in df_clean.columns:
        # Check if object column is actually numeric with currencies / commas
        if df_clean[col].dtype == "object":
            sample = df_clean[col].dropna().astype(str).head(50)
            if len(sample) > 0:
                # Check for currency or numeric patterns
                num_like = sum(bool(re.match(r"^[\$₹€£]?\s*[-+]?[\d,]+(\.\d+)?%?$", s.strip())) for s in sample)
                if num_like / len(sample) >= 0.7:
                    df_clean[col] = df_clean[col].apply(lambda x: clean_numeric_value(x, default=np.nan))
                    continue

                # Check if date
                try:
                    date_sample = pd.to_datetime(sample, errors="coerce")
                    if date_sample.notna().sum() / len(sample) >= 0.7:
                        df_clean[col] = pd.to_datetime(df_clean[col], errors="coerce")
                        continue
                except Exception:
                    pass

    return df_clean


class UniversalDataProfiler:
    """Profiles any dataset, detecting semantic roles, statistics, and anomalies."""

    def __init__(self, df: pd.DataFrame, dataset_name: str = "Dataset"):
        self.df = clean_dataframe(df)
        self.dataset_name = dataset_name
        self.profile = {}
        self._analyze()

    def _analyze(self):
        df = self.df
        total_rows, total_cols = df.shape

        col_types = {}
        numeric_cols = []
        categorical_cols = []
        datetime_cols = []
        id_cols = []
        target_candidates = []

        # Keywords for semantic heuristic scoring
        METRIC_KEYWORDS = ["sale", "revenue", "profit", "amount", "price", "cost", "total", "spend", "balance",
                           "due", "salary", "score", "value", "gpa", "rating", "fare", "fee", "volume", "qty", "quantity"]
        TARGET_KEYWORDS = ["target", "label", "churn", "exited", "status", "converted", "default", "outcome",
                           "fraud", "class", "result", "sentiment", "risk", "attrition", "response"]
        ID_KEYWORDS = ["id", "code", "uuid", "key", "number", "no", "ssn", "isbn"]

        for col in df.columns:
            c_lower = col.lower()
            dtype = df[col].dtype

            if pd.api.types.is_datetime64_any_dtype(dtype):
                col_types[col] = "datetime"
                datetime_cols.append(col)
            elif pd.api.types.is_numeric_dtype(dtype):
                unique_count = df[col].nunique()
                # Check if it looks like an ID
                if any(k in c_lower for k in ID_KEYWORDS) and unique_count > (total_rows * 0.8):
                    col_types[col] = "id"
                    id_cols.append(col)
                elif unique_count <= 2 and any(k in c_lower for k in TARGET_KEYWORDS):
                    col_types[col] = "binary_target"
                    target_candidates.append(col)
                    numeric_cols.append(col)
                else:
                    col_types[col] = "numeric"
                    numeric_cols.append(col)
                    if any(k in c_lower for k in TARGET_KEYWORDS):
                        target_candidates.append(col)
            else:
                # Text or categorical
                unique_count = df[col].nunique()
                if unique_count == total_rows or (unique_count > total_rows * 0.8 and any(k in c_lower for k in ID_KEYWORDS)):
                    col_types[col] = "id"
                    id_cols.append(col)
                elif unique_count <= 50 or (unique_count / max(1, total_rows) < 0.2):
                    col_types[col] = "categorical"
                    categorical_cols.append(col)
                    if any(k in c_lower for k in TARGET_KEYWORDS):
                        target_candidates.append(col)
                else:
                    col_types[col] = "text_dimension"
                    categorical_cols.append(col)

        # Disambiguate Primary Value Metric
        # Score numeric columns based on name match and variance
        best_metric = None
        best_metric_score = -1
        for col in numeric_cols:
            c_lower = col.lower()
            score = 0
            for kw in METRIC_KEYWORDS:
                if kw in c_lower:
                    score += 10
            # Prefer columns with positive numbers and non-zero variance
            s_mean = df[col].mean()
            s_sum = df[col].sum()
            if s_mean > 0:
                score += 5
            if s_sum > 100:
                score += 5
            if col in target_candidates:
                score -= 10
            if any(k in c_lower for k in ID_KEYWORDS):
                score -= 20
            if score > best_metric_score:
                best_metric_score = score
                best_metric = col

        if not best_metric and numeric_cols:
            best_metric = numeric_cols[0]

        # Detailed column summary statistics
        stats = {}
        for col in df.columns:
            missing_count = int(df[col].isna().sum())
            missing_pct = round((missing_count / max(1, total_rows)) * 100, 2)
            u_count = int(df[col].nunique())

            col_stat = {
                "dtype": str(df[col].dtype),
                "inferred_type": col_types.get(col, "unknown"),
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "unique_count": u_count,
            }

            if col in numeric_cols:
                series = df[col].dropna()
                if len(series) > 0:
                    q25 = float(series.quantile(0.25))
                    q75 = float(series.quantile(0.75))
                    iqr = q75 - q25
                    outliers = int(((series < (q25 - 1.5 * iqr)) | (series > (q75 + 1.5 * iqr))).sum())
                    col_stat.update({
                        "min": float(series.min()),
                        "max": float(series.max()),
                        "mean": round(float(series.mean()), 2),
                        "median": round(float(series.median()), 2),
                        "std": round(float(series.std()), 2) if len(series) > 1 else 0.0,
                        "sum": round(float(series.sum()), 2),
                        "zero_count": int((series == 0).sum()),
                        "outlier_count": outliers,
                    })
            elif col in categorical_cols:
                vc = df[col].value_counts().head(5).to_dict()
                col_stat["top_values"] = {str(k): int(v) for k, v in vc.items()}

            elif col in datetime_cols:
                d_series = df[col].dropna()
                if len(d_series) > 0:
                    col_stat["min_date"] = str(d_series.min())[:10]
                    col_stat["max_date"] = str(d_series.max())[:10]
                    col_stat["date_span_days"] = (d_series.max() - d_series.min()).days

            stats[col] = col_stat

        # Compute numerical correlations
        correlations = {}
        if len(numeric_cols) >= 2:
            try:
                corr_matrix = df[numeric_cols].corr()
                for c1 in numeric_cols:
                    correlations[c1] = {}
                    for c2 in numeric_cols:
                        if c1 != c2:
                            val = corr_matrix.loc[c1, c2]
                            if not np.isnan(val):
                                correlations[c1][c2] = round(float(val), 3)
            except Exception:
                pass

        # Data Quality Score (0 to 100)
        missing_penalties = sum(s["missing_pct"] for s in stats.values()) / max(1, len(stats))
        quality_score = max(10.0, round(100.0 - (missing_penalties * 1.5), 1))

        self.profile = {
            "dataset_name": self.dataset_name,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "data_quality_score": quality_score,
            "semantic_roles": {
                "primary_metric": best_metric,
                "numeric_metrics": [c for c in numeric_cols if c != best_metric],
                "dimensions": categorical_cols,
                "temporal": datetime_cols,
                "identifiers": id_cols,
                "target_candidates": target_candidates,
            },
            "columns": stats,
            "correlations": correlations,
        }

    def get_profile(self) -> dict:
        return self.profile

    def get_profile_json(self) -> str:
        return json.dumps(self.profile, indent=2, default=str)


def load_any_dataset(file_path: str) -> pd.DataFrame:
    """Reads Excel (multi-sheet or single), CSV, Parquet, or JSON into a DataFrame."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        excel = pd.ExcelFile(file_path)
        # If multiple sheets, pick the one with most rows or combine
        sheet_rows = {}
        for s in excel.sheet_names:
            df_temp = pd.read_excel(excel, sheet_name=s)
            sheet_rows[s] = len(df_temp)
        best_sheet = max(sheet_rows, key=sheet_rows.get)
        df = pd.read_excel(file_path, sheet_name=best_sheet)
    elif ext == ".csv":
        # Try utf-8 first, fallback to latin-1
        try:
            df = pd.read_csv(file_path)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="latin-1")
    elif ext == ".parquet":
        df = pd.read_parquet(file_path)
    elif ext == ".json":
        df = pd.read_json(file_path)
    else:
        raise ValueError(f"Unsupported format '{ext}'.")

    return clean_dataframe(df)
