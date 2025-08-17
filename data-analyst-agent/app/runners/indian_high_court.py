
import re, time, duckdb, math
from ..utils import time_budget_ok, fig_to_base64_png
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def can_handle(task_text: str) -> bool:
    return "indian high court judgement dataset" in task_text.lower() or "ecourts" in task_text.lower()

def _connect():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL parquet; LOAD parquet;")
    return con

def run(task_text: str, files: dict, start_time: float):
    # Extract questions listed in JSON-like or lines
    # We assume the evaluator expects a JSON object with 3 keys (see prompt)
    result = {
        "Which high court disposed the most cases from 2019 - 2022?": None,
        "What's the regression slope of the date_of_registration - decision_date by year in the court=33_10?": None,
        "Plot the year and # of days of delay from the above question as a scatterplot with a regression line. Encode as a base64 data URI under 100,000 characters": None
    }
    try:
        con = _connect()
        # Q1
        if not time_budget_ok(start_time): return result
        q1 = con.execute("""
            SELECT court, COUNT(*) as n
            FROM read_parquet('s3://indian-high-court-judgments/metadata/parquet/year=*/court=*/bench=*/metadata.parquet?s3_region=ap-south-1')
            WHERE year BETWEEN 2019 AND 2022
            GROUP BY court
            ORDER BY n DESC
            LIMIT 1
        """).fetchdf()
        if len(q1):
            result["Which high court disposed the most cases from 2019 - 2022?"] = str(q1.iloc[0]['court'])
        # Q2 + Q3
        if not time_budget_ok(start_time): return result
        df = con.execute("""
            SELECT date_of_registration, decision_date, year
            FROM read_parquet('s3://indian-high-court-judgments/metadata/parquet/year=*/court=33_10/bench=*/metadata.parquet?s3_region=ap-south-1')
        """).fetchdf()
        # Clean dates
        df['date_of_registration'] = pd.to_datetime(df['date_of_registration'], errors='coerce', dayfirst=True)
        df['decision_date'] = pd.to_datetime(df['decision_date'], errors='coerce')
        df = df.dropna(subset=['date_of_registration','decision_date','year'])
        df['delay_days'] = (df['decision_date'] - df['date_of_registration']).dt.days
        # regression slope by year (delay ~ year)
        x = df['year'].astype(float).values
        y = df['delay_days'].astype(float).values
        if len(x) >= 2:
            m, b = np.polyfit(x, y, 1)
            result["What's the regression slope of the date_of_registration - decision_date by year in the court=33_10?"] = float(round(m, 6))
        # plot
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.scatter(df['year'], df['delay_days'])
        if len(x) >= 2:
            xs = np.linspace(df['year'].min(), df['year'].max(), 100)
            ys = m*xs + b
            ax.plot(xs, ys, linestyle=':', color='red')
        ax.set_xlabel('Year')
        ax.set_ylabel('Delay (days)')
        ax.set_title('Delay vs Year (court=33_10)')
        result["Plot the year and # of days of delay from the above question as a scatterplot with a regression line. Encode as a base64 data URI under 100,000 characters"] = fig_to_base64_png(fig, max_bytes=100_000)
        return result
    except Exception as e:
        # Return best-effort structure
        return result
