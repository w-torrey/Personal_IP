# IndexPulse

IndexPulse is a self-hosted OSINT (Open Source Intelligence) monitoring dashboard built on Google Dorks. You define watchlists for the keywords, people, brands or domains you care about, and IndexPulse runs targeted searches against them every day. It saves new results as alerts and uses Claude to write a short digest and dossier for each watchlist.

It's meant for security teams that need to keep watch on public information about executive protection, brand reputation, cyber threat intelligence, or any other keyword asset.

> **Note:** This is my personal fork of IndexPulse, where I try out individual changes and experiments. The main focus right now is turning the AI summary tool into an agentic workflow, so expect it to differ from the original project.

**Live demo:** (https://indexpulse-23p2.onrender.com/). Register any email and password to look around.

## Features

- **Watchlists:** define targets and the dork operators to apply to them, with a live preview of the generated query
- **Daily sweeps:** APScheduler runs every watchlist at 8 PM; you can also trigger a run on demand
- **Alerts:** new results are deduplicated, saved, and shown in the dashboard, where you can mark them as read
- **AI investigation:** for each watchlist with new results, a Claude agent opens the source pages and checks past alerts and briefings before writing the daily digest; a standing dossier is kept up to date as well
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

## Running locally

IndexPulse runs entirely on your own machine: one Python process serves both the API and the dashboard.

### Prerequisites

- Python 3.10+
- Node.js 20.19+ (required by Vite 8)
- PostgreSQL, running locally
- A SerpAPI key and an Anthropic API key

### 1. Clone and create the database

```bash
git clone https://github.com/w-torrey/Personal_IP.git
cd Personal_IP
createdb IndexPulse
```

You only need an empty database. The backend creates its tables from `docs/schema.sql` the first time it starts.

### 2. Configure the backend

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r reqs.txt
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string, e.g. `postgresql://postgres:yourpassword@localhost:5432/IndexPulse` |
| `SERPAPI_KEY` | SerpAPI key used for dork searches |
| `ANTHROPIC_API_KEY` | Anthropic API key used for digests and dossiers |
| `SECRET_KEY` | Key used to sign login tokens. Required; generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

### 3. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Start the app

```bash
cd backend
uvicorn main:app --port 8000
```

Open http://localhost:8000, register an account, and create your first watchlist.

The daily sweep runs at 8 PM while the app is running. Use the dashboard's run button to sweep on demand.

### Frontend development

To work on the frontend with hot reload, keep the backend running and start the Vite dev server in a second terminal:

```bash
cd frontend
VITE_API_BASE=http://localhost:8000 npm run dev   # PowerShell: $env:VITE_API_BASE="http://localhost:8000"; npm run dev
```

Then open http://localhost:5173.

## Deploying to Render

The repo includes a `Dockerfile` and a `render.yaml` blueprint that set up the app and a Postgres database on [Render](https://render.com/).

1. Push the repo to GitHub.
2. In Render, choose **New > Blueprint** and select the repo.
3. Enter your `SERPAPI_KEY` and `ANTHROPIC_API_KEY` when prompted. Render generates `SECRET_KEY` and connects the database for you.

The app creates its tables on first start. On the free plan the service sleeps when idle, so the first visit after a while takes up to a minute, and the 8 PM sweep only runs if the service is awake.

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

## Project structure

```
├── backend/
│   ├── main.py                    # FastAPI app, routes, CORS, static file serving
│   ├── auth.py                    # Password hashing and JWT handling
│   ├── database.py                # PostgreSQL data layer
│   ├── dork_engine.py             # Dork query builder and SerpAPI client
│   ├── scheduler.py               # Daily and on-demand watchlist sweeps
│   ├── investigator.py            # Agentic digest: reads source pages and checks history before writing
│   ├── summary_engine.py          # Dossier generation, and the fallback single-call digest
│   └── .env.example
├── docs/
│   ├── components.md              # Component overview
│   ├── schema.sql                 # Database schema, applied on startup
│   ├── ERD_2_IndexPulse.png       # Entity relationship diagram
│   └── SysArch_Index_Pulse.png    # System architecture diagram
├── frontend/
│   ├── src/                       # React app (App.jsx, main.jsx, index.css)
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── Dockerfile                     # Builds the frontend and runs the backend in one image
├── render.yaml                    # Render blueprint (web service + Postgres)
└── reqs.txt
```

## Authors

Jackson Morrow, Will Torrey, Chris Doucette
