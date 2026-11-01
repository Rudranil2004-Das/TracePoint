# TRACEPOINT — Autonomous Data Intelligence

A local-first analytics workspace for CSV and Excel datasets. It computes descriptive statistics, data quality signals, correlations, category summaries, cautious date-indexed exploratory forecasts, automatic management Q&A and executive PDF reports. Gemini commentary is optional; the statistical engine works without an API key.

## Requirements
- Windows 11
- Python 3.12
- Node.js 18+ and npm

## Setup (PowerShell)
Open two VS Code terminals from the project root (`C:\Startup`, or the extracted folder).

### 1. Backend
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env -Force
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
API health: http://127.0.0.1:8000/api/health
API docs: http://127.0.0.1:8000/docs

### 2. Frontend (second terminal)
```powershell
cd frontend
npm install
Copy-Item .env.example .env -Force
npm run dev
```
Open the Vite URL shown in the terminal (normally http://127.0.0.1:5173).

## Optional Gemini
Add `GEMINI_API_KEY=your_key` to `backend/.env` and enable AI analyst commentary before running an analysis. Keep the key in the backend only. Without a key, local analytics, Q&A and PDF export remain available.

## Features
- CSV, XLSX and XLS ingestion (25 MB upload cap; 250,000 row and 200 column caps)
- Numeric/categorical/date detection, summary statistics, missing values, duplicates and IQR outlier screening
- Correlation and dynamic category/distribution charts
- Automatic dataset-grounded management questions and answers
- Forecast estimates only when a usable date field and at least eight distinct periods exist; otherwise a clear limitation is shown
- Four dashboard workspaces: Executive overview, Data analysis, Prediction & quality, Business intelligence
- SQLite persistence for analysis results across backend restarts
- Corporate PDF executive report

## Notes and limitations
- Forecasting is intentionally exploratory linear regression over date-aggregated observations; its residual interval is approximate and does not model seasonality or external drivers.
- Correlation does not imply causation. IQR outliers are review candidates, not automatically invalid values.
- Database-source ingestion and read-only database connectors are not implemented in this release. The current ingestion path is file upload.
- Large-file processing is bounded by the limits above and available machine memory.
- Gemini is optional and may fail independently; local results remain available.
- SQLite is local by default. Do not expose the development server to untrusted networks.

## Tests
From `backend` with the virtual environment active:
```powershell
pytest -q
```
