
# Data Analyst Agent (FastAPI)

An API that uses programmatic heuristics (and optional LLM extensions) to **source, prepare, analyze, and visualize data** within a strict time budget.

> Endpoint: `POST /api/` (multipart/form-data)

## Features

- Accepts `questions.txt` (**required**) and any number of additional files (CSV/Parquet/Images).
- Task runners:
  - **Wikipedia Highest-Grossing Films**: scrapes the table and answers 4 sub-questions, including a base64 PNG scatterplot with a **dotted red** regression line (under 100 KB).
  - **Indian High Court Dataset**: runs DuckDB HTTPFS queries against the public S3 parquet (best-effort within time budget) and returns required answers including a base64 plot.
  - **Generic CSV/Parquet Fallback**: computes correlations/plots when requested and returns a summary.
- Always returns a JSON structure even on partial failure (for scoring).
- 3-minute guardrail with internal time budget (≈160s) to stay safe with retries.

## Quickstart (local)

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Test locally

```bash
echo "Scrape the list of highest grossing films from Wikipedia. It is at the URL:
https://en.wikipedia.org/wiki/List_of_highest-grossing_films

Answer the following questions and respond with a JSON array of strings containing the answer.

1. How many $2 bn movies were released before 2000?
2. Which is the earliest film that grossed over $1.5 bn?
3. What's the correlation between the Rank and Peak?
4. Draw a scatterplot of Rank and Peak along with a dotted red regression line through it.
   Return as a base-64 encoded data URI, \"data:image/png;base64,iVBORw0KG...\" under 100,000 bytes." > questions.txt

curl -s -X POST "http://localhost:8000/api/" \
  -F "questions=@questions.txt" | jq .
```

## Docker

```bash
docker build -t data-analyst-agent .
docker run -p 8000:8000 data-analyst-agent
```

## Deploy (Render example)

1. Create a new **Web Service** on [Render](https://render.com/).
2. Connect your public GitHub repo containing this project.
3. Environment:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
   - Set **Port** to `10000` (or your chosen port).
4. After deploy, your endpoint will be `https://<service>.onrender.com/api/`.

> Railway, Fly.io, or Azure Web Apps work similarly.

## API

`POST /api/`

- **Form fields**
  - `questions` (file): **required**. The plain-text instructions.
  - `files` (file): zero or more attachments. Examples: `data.csv`, images, parquet, etc.

- **Response**
  - JSON (array or object) depending on the runner. The Wikipedia runner returns a 4-element array, matching the sample rubric.

### Example (with attachments)

```bash
curl "http://localhost:8000/api/" \
  -F "questions=@questions.txt" \
  -F "files=@data.csv" \
  -F "files=@image.png"
```

## Code Structure

```
app/
  main.py                 # FastAPI app + routing
  utils.py                # helpers (time budget, base64 PNG)
  runners/
    wiki_top_grossing.py  # Wikipedia sample task
    indian_high_court.py  # DuckDB + S3 sample task
    generic_csv.py        # Fallback analysis
requirements.txt
Dockerfile
LICENSE (MIT)
README.md
```

## Notes

- The Indian High Court S3 queries may take time or be rate-limited; the service returns best-effort answers and always preserves the JSON shape.
- To add more runners, drop a `your_task.py` file in `app/runners/` with `can_handle()` and `run()`.
- Optional LLM integration can be added via an environment variable (e.g., `OPENAI_API_KEY`) and a new runner. This template avoids remote LLM calls to keep responses within the time budget reliably.
