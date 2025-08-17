
import re, time, io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from . import runner_base
from ..utils import time_budget_ok, fig_to_base64_png

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_highest-grossing_films"

def can_handle(task_text: str) -> bool:
    return "highest grossing" in task_text.lower() and "wikipedia" in task_text.lower()

def run(task_text: str, files: dict, start_time: float):
    # Load the page and parse tables
    resp = requests.get(WIKI_URL, timeout=20)
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    # Heuristically find the main "Highest-grossing films" table
    main = None
    for t in tables:
        cols = [c.lower() for c in t.columns]
        if any("rank" in str(c).lower() for c in cols) and any("peak" in str(c).lower() for c in cols):
            main = t.copy()
            break
    if main is None:
        raise RuntimeError("Could not find the main table on Wikipedia page.")
    # Normalize columns
    main.columns = [re.sub(r'\[.*?\]', '', str(c)).strip() for c in main.columns]
    # Some wikitables have MultiIndex; flatten if needed
    if isinstance(main.columns, pd.MultiIndex):
        main.columns = [' '.join([str(x) for x in tup if x and x!='nan']).strip() for tup in main.columns]
    # Keep necessary columns
    # Try common variants
    colmap = {}
    for c in main.columns:
        cl = c.lower()
        if 'rank' in cl and 'rank' not in colmap: colmap['Rank'] = c
        if 'peak' in cl and 'peak' not in colmap: colmap['Peak'] = c
        if 'title' in cl and 'Title' not in colmap: colmap['Title'] = c
        if ('year' in cl or 'release' in cl) and 'Year' not in colmap: colmap['Year'] = c
        if ('worldwide' in cl or 'gross' in cl) and 'Worldwide' not in colmap: colmap['Worldwide'] = c
    df = main.rename(columns={v:k for k,v in colmap.items()})
    # Clean values
    if 'Year' in df:
        df['Year'] = pd.to_numeric(df['Year'].astype(str).str.extract(r'(\d{4})')[0], errors='coerce')
    if 'Worldwide' in df:
        # Extract numeric dollars
        df['Worldwide_num'] = (df['Worldwide'].astype(str)
                               .str.replace(',', '', regex=False)
                               .str.replace(r'[^0-9.]', '', regex=True)
                               .astype(float))
    # Q1: How many $2 bn movies were released before 2000?
    q1 = int(((df.get('Worldwide_num', pd.Series(dtype=float)) >= 2_000_000_000.0) & (df.get('Year') < 2000)).sum())
    # Q2: earliest film that grossed over $1.5 bn
    over = df[df.get('Worldwide_num', 0) > 1_500_000_000.0].copy()
    earliest_title = None
    if not over.empty:
        # sort by Year ascending, then Worldwide desc to break ties
        over = over.sort_values(['Year','Worldwide_num'], ascending=[True, False])
        earliest_title = str(over.iloc[0].get('Title'))
    # Q3: correlation between Rank and Peak
    corr = np.nan
    try:
        rank = pd.to_numeric(df['Rank'], errors='coerce')
        peak = pd.to_numeric(df['Peak'], errors='coerce')
        valid = rank.notna() & peak.notna()
        if valid.any():
            corr = float(rank[valid].corr(peak[valid]))
    except Exception:
        pass
    # Q4: scatter with dotted red regression
    img_uri = None
    try:
        rank = pd.to_numeric(df['Rank'], errors='coerce')
        peak = pd.to_numeric(df['Peak'], errors='coerce')
        valid = rank.notna() & peak.notna()
        x = rank[valid].values
        y = peak[valid].values
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.scatter(x, y)
        # regression line
        if len(x) >= 2:
            m, b = np.polyfit(x, y, 1)
            xs = np.linspace(min(x), max(x), 100)
            ys = m*xs + b
            ax.plot(xs, ys, linestyle=':', color='red')  # dotted red
        ax.set_xlabel('Rank')
        ax.set_ylabel('Peak')
        ax.set_title('Rank vs Peak')
        img_uri = fig_to_base64_png(fig, max_bytes=100_000)
    except Exception:
        img_uri = None
    return [q1, earliest_title, round(corr, 6) if corr==corr else None, img_uri]
