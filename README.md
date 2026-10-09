# IndexPulse

IndexPulse is a self-hosted OSINT (Open Source Intelligence) monitoring dashboard built on Google Dorks. You define watchlists for the keywords, people, brands or domains you care about, and IndexPulse runs targeted searches against them every day. It saves new results as alerts and uses Claude to write a short digest and dossier for each watchlist.

It's meant for security teams that need to keep watch on public information about executive protection, brand reputation, cyber threat intelligence, or any other keyword asset.

> **Note:** This is my personal fork of IndexPulse, where I try out individual changes and experiments. The main focus right now is turning the AI summary tool into an agentic workflow, so expect it to differ from the original project.

## Features

- **Watchlists:** define targets and the dork operators to apply to them, with a live preview of the generated query
- **Daily sweeps:** APScheduler runs every watchlist at 8 PM; you can also trigger a run on demand
- **Alerts:** new results are deduplicated, saved, and shown in the dashboard, where you can mark them as read
- **AI summaries:** each run produces a digest and dossier through the Anthropic API
- **Authentication:** user registration and login with bcrypt-hashed passwords and JWT-protected routes

## What is a Google Dork?

A Google Dork is a search query that uses Google's advanced operators to find specific content that a normal keyword search would miss. IndexPulse's dork engine combines these operators automatically when it builds a query for a target:

| Operator | Effect |
|----------|--------|
| `site:` | Limits results to one domain (e.g. `site:linkedin.com`) |
| `filetype:` | Limits results to a file type, such as PDF or DOCX |
| `intitle:` / `intext:` | Requires a keyword in the page title or body |
| `"quoted phrase"` | Forces an exact match |
| `-keyword` | Excludes results that contain a keyword |

Queries run through [SerpAPI](https://serpapi.com/).

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy / psycopg2, APScheduler
- **Database:** PostgreSQL
- **Frontend:** React 19, Vite
- **External APIs:** SerpAPI (search), Anthropic (summaries)

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 20.19+ (required by Vite 8)
- PostgreSQL
- A SerpAPI key and an Anthropic API key

### 1. Database

Create a database and load the schema:

```bash
createdb IndexPulse
psql -d IndexPulse -f docs/schema.sql
```

### 2. Backend

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r reqs.txt
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (defaults to `postgresql://postgres@localhost:5432/IndexPulse`) |
| `SERPAPI_KEY` | SerpAPI key used for dork searches |
| `ANTHROPIC_API_KEY` | Anthropic API key used for digests and dossiers |

### 3. Frontend

```bash
cd frontend
npm install
npm run build
```

The backend serves the built frontend from `frontend/dist`. Before building, set `API_BASE` at the top of `frontend/src/App.jsx` to your backend's address.

For frontend development with hot reload, run `npm run dev` instead.

### 4. Run

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`, register an account, and create your first watchlist.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create an account |
| `POST` | `/auth/login` | Log in and receive a JWT |
| `GET` | `/watchlists` | List watchlists |
| `POST` | `/watchlist` | Create a watchlist |
| `PUT` | `/watchlist/{id}` | Update a watchlist |
| `DELETE` | `/watchlist/{id}` | Delete a watchlist |
| `POST` | `/search` | Run a one-off dork search |
| `POST` | `/monitor` | Run monitoring for a target |
| `POST` | `/run-now` | Run all watchlists immediately |
| `GET` | `/alerts` | List alerts |
| `PATCH` | `/alerts/{id}/read` | Mark an alert as read |
| `GET` | `/digests` | List generated digests |
| `GET` | `/dossiers` | List generated dossiers |

## Deployment

There are two ways to deploy:

- **GitHub Actions:** `.github/workflows/deploy.yml` runs on a self-hosted runner whenever you push to `main`. It pulls the code, rebuilds the frontend, and restarts an `indexpulse` systemd service.
- **Manual:** `deploy.sh` pulls `main`, rebuilds the frontend, and restarts uvicorn in the background, logging to `deploy.log`.

Both use hard-coded paths under `/home/ipuser/IndexPulse`, so change those to match your server.

## Project structure

```
├── .github/workflows/deploy.yml   # CI deploy workflow
├── backend/
│   ├── main.py                    # FastAPI app, routes, CORS, static file serving
│   ├── auth.py                    # Password hashing and JWT handling
│   ├── database.py                # PostgreSQL data layer
│   ├── dork_engine.py             # Dork query builder and SerpAPI client
│   ├── scheduler.py               # Daily and on-demand watchlist sweeps
│   ├── summary_engine.py          # Anthropic digest and dossier generation
│   └── .env.example
├── docs/
│   ├── components.md              # Component overview
│   ├── schema.sql                 # Database schema
│   ├── ERD_2_IndexPulse.png       # Entity relationship diagram
│   └── SysArch_Index_Pulse.png    # System architecture diagram
├── frontend/
│   ├── src/                       # React app (App.jsx, main.jsx, index.css)
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── deploy.sh
└── reqs.txt
```

## Authors

Jackson Morrow, Will Torrey, Chris Doucette
