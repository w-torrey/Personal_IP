# IndexPulse

IndexPulse is a self-hosted OSINT (Open Source Intelligence) monitoring dashboard built on Google Dorks. You define watchlists for the keywords, people, brands or domains you care about, and IndexPulse runs targeted searches against them every day. It saves new results as alerts and uses Claude to write a short digest and dossier for each watchlist.

It's meant for security teams that need to keep watch on public information about executive protection, brand reputation, cyber threat intelligence, or any other keyword asset.

> **Note:** This is my personal fork of IndexPulse, where I try out individual changes and experiments. The main focus right now is turning the AI summary tool into an agentic workflow, so expect it to differ from the original project.

**Live demo:** [indexpulse-23p2.onrender.com](https://indexpulse-23p2.onrender.com/). Register any email and password to look around. The demo runs on a free plan, so the first visit after a quiet spell can take up to a minute to load.

## Quick tour

1. **Sign up.** On the login screen, choose **Sign up** and register with any email and password.
2. **Add a watchlist.** Click **+ Add watchlist** and fill in the form using the example below. Press **Enter** after each value so it turns into a tag; text left in a box without pressing Enter is ignored. The query preview at the bottom shows the exact search that will be sent.
3. **Run a sweep.** Click **Run now** to search every watchlist immediately, rather than waiting for the nightly 8 PM run. New results show up as alert cards in their category's column.
4. **Investigate.** Click **edit** in the **Threat Intelligence** column header to open the watchlist manager, then click **Investigate**. The agent reads the source articles and compares them with earlier results before writing a briefing. This takes a minute or so. When it's done, a line under the watchlist shows how long it took, which tools it used and the headline.
5. **Read the briefing.** Click the **Threat Intelligence** column header to open its summaries: the latest digest and the running dossier.
6. **See how it was built.** Under the digest, click **How this was built →** to step through the agent's investigation: what it was thinking, which pages it opened and what it checked.

### Example watchlist

This one returns fresh results on almost any day, because ransomware is covered constantly by security news sites:

| Field | Value |
|-------|-------|
| Label | `Ransomware attacks` |
| Category | `Threat Intelligence` |
| Keywords | `ransomware` |
| Or keywords | `attack`, `breach`, `leak site` |
| Exclude keywords | `webinar` |
| Include sites | `bleepingcomputer.com`, `therecord.media`, `securityweek.com` |

It searches Google for:

```
"ransomware" -"webinar" ("attack" OR "breach" OR "leak site") (site:bleepingcomputer.com OR site:therecord.media OR site:securityweek.com)
```

Searches only cover the last 24 hours. If a sweep finds nothing, remove the include sites to search the whole web.

## How the AI investigation works

A Google result is only a title and a one- or two-line snippet, which is usually too little to judge what happened. So rather than summarising snippets in a single call, IndexPulse hands each watchlist's new results to a Claude agent (`backend/investigator.py`) that investigates before it writes.

```
new alerts (title, URL, snippet)
        │
        ▼
 ┌──────────────── Claude agent ────────────────┐
 │ 1. Triage: which results matter?             │
 │ 2. Read: open the important articles         │ ──► web_fetch
 │ 3. Compare: seen before? what changed?       │ ──► get_alert_history, get_previous_digests
 │ 4. Write: headline, narrative, severity      │
 └──────────────────────────────────────────────┘
        │
        ▼
 digest saved to the database and shown on the dashboard
```

The agent decides for itself which tools to use and how often. A clear-cut result may need nothing beyond its snippet, while an ambiguous one gets opened and checked against history.

### Tools

| Tool | What it does | Why the agent needs it |
|------|--------------|------------------------|
| `web_fetch` | Opens a result's URL and reads the full article. Runs on Anthropic's servers, and can only open URLs already in the conversation. | Snippets are too thin to tell a real incident from a passing mention |
| `get_alert_history` | Returns up to 50 of this watchlist's earlier results | Separates new developments from stories already reported |
| `get_previous_digests` | Returns up to 5 of this watchlist's recent briefings | Lets the briefing say what changed since last time |

Both database tools are read-only and locked to the watchlist being investigated, so the agent can't read other watchlists.

### Output

The agent's final answer must match a fixed schema: a headline, a 2–4 sentence narrative, a severity of `low`, `medium` or `high`, and the IDs of the alerts it's based on. The alert IDs are restricted to the alerts it was given, so it can't cite results that don't exist. The dashboard reads the same format as before, so no frontend changes were needed.

### Guardrails

- **Untrusted content:** fetched pages and snippets are third-party text, and a page could contain instructions aimed at the model. The system prompt tells the agent to treat them as evidence to assess, never as instructions, and none of its tools can change anything.
- **Grounding:** every statement must come from what it read. Claims that rest only on a snippet it couldn't open are flagged as such.
- **Cost limits:** at most 5 page fetches per investigation (each capped at 8,000 tokens of content) and 8 rounds of database-tool calls.
- **Fallbacks:** if an investigation fails, the sweep falls back to a single-call digest, so it always produces a briefing. If Claude's safety checks decline a request, Anthropic retries it on another model.

### Investigation trace

Every investigated digest keeps a step-by-step record of how it was built. In a category's summaries, click **How this was built →** under a digest to see:

- the agent's reasoning at each step (Claude's summarised thinking)
- each tool it called and with what: the page it opened, or how much history it pulled
- what came back: the title of each page read, pages that couldn't be opened, and how many past records it checked
- the time taken, the tokens used, and the briefing it ended with

Digests written by the single-call fallback have no trace, so the button doesn't appear on them.

### When it runs

- **Nightly sweep:** every watchlist with new results is investigated automatically at 8 PM.
- **On demand:** the **Investigate** button in the watchlist manager (`POST /watchlist/{id}/investigate`) runs it on a watchlist's 10 most recent alerts, whether or not they're new. It reports how long it took and which tools it used, which makes it handy for testing.

Built with the Anthropic Python SDK's Tool Runner on `claude-opus-5-5`.

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
| `POST` | `/watchlist/{id}/investigate` | Run the AI investigator on a watchlist's recent alerts and save the digest |
| `GET` | `/digests/{id}/trace` | Step-by-step trace of the investigation behind a digest |
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
