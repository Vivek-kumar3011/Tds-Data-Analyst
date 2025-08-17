
import io, re, time, json, math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ..utils import time_budget_ok, fig_to_base64_png

def can_handle(task_text: str) -> bool:
    return True  # fallback

def run(task_text: str, files: dict, start_time: float):
    """
    A minimal fallback runner:
    - If a CSV/Parquet file is provided, load it into Pandas.
    - If task asks for 'correlation X Y', compute Pearson.
    - If task asks 'scatter X Y', plot and return base64.
    - Otherwise, return a short summary.
    """
    # Find first tabular file
    df = None
    for name, f in files.items():
        if name.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(f))
            break
        if name.lower().endswith('.parquet'):
            df = pd.read_parquet(io.BytesIO(f))
            break
    if df is None:
        return {"summary": "No tabular data attached. Provide a CSV or Parquet for generic analysis."}
    task = task_text.lower()
    out = {}
    # Correlation
    m = re.search(r'correlation\s+between\s+([a-z0-9_]+)\s+and\s+([a-z0-9_]+)', task)
    if m:
        a, b = m.group(1), m.group(2)
        if a in df.columns and b in df.columns:
            out['correlation'] = float(df[a].corr(df[b]))
    # Scatter
    m2 = re.search(r'scatter(?:plot)?\s+of\s+([a-z0-9_]+)\s+and\s+([a-z0-9_]+)', task)
    if m2:
        a, b = m2.group(1), m2.group(2)
        if a in df.columns and b in df.columns:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.scatter(df[a], df[b])
            # regression
            try:
                x = pd.to_numeric(df[a], errors='coerce')
                y = pd.to_numeric(df[b], errors='coerce')
                ok = x.notna() & y.notna()
                if ok.sum() >= 2:
                    m, bb = np.polyfit(x[ok], y[ok], 1)
                    xs = np.linspace(x[ok].min(), x[ok].max(), 100)
                    ys = m*xs + bb
                    ax.plot(xs, ys, linestyle=':', color='red')
            except Exception:
                pass
            ax.set_xlabel(a)
            ax.set_ylabel(b)
            out['plot'] = fig_to_base64_png(fig)
    # Basic describe
    out['columns'] = list(df.columns)
    out['shape'] = list(df.shape)
    return out
