from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dork_engine import run_dork
from database import save_results, get_or_create_watchlist, get_new_alerts, get_all_watchlists
from scheduler import start_scheduler, stop_scheduler, run_all_watchlists
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler(interval_hours=24)
    yield
    stop_scheduler()

app = FastAPI(
    title="IndexPulse API",
    description="OSINT Google Dork Monitoring Engine",
    version="0.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DorkRequest(BaseModel):
    person: str
    organization: str
    hours: Optional[int] = 24
    num_results: Optional[int] = 10
    category: Optional[str] = "Uncategorized"

@app.get("/")
def root():
    return {"status": "IndexPulse is running"}

@app.get("/search")
def search(person: str, organization: str, hours: int = 24, num_results: int = 10):
    result = run_dork(person=person, organization=organization, hours=hours, num_results=num_results)
    if not result["success"]:
        raise HTTPException(status_code=500, detail="SerpApi call failed")
    return result

@app.post("/monitor")
def monitor(request: DorkRequest):
    watchlist_id = get_or_create_watchlist(request.person, request.organization, request.category)
    result = run_dork(request.person, request.organization, request.hours, request.num_results)
    if not result["success"]:
        raise HTTPException(status_code=500, detail="SerpApi call failed")
    saved = save_results(watchlist_id, result["results"])
    return {"watchlist_id": watchlist_id, "results": result["results"], "db": saved}

@app.get("/alerts")
def alerts():
    return get_new_alerts()

@app.get("/watchlists")
def get_watchlists():
    return get_all_watchlists()

@app.post("/watchlist")
def create_watchlist(request: DorkRequest):
    watchlist_id = get_or_create_watchlist(request.person, request.organization, request.category)
    return {"watchlist_id": watchlist_id, "person": request.person, "organization": request.organization, "category": request.category}

@app.post("/run-now")
def run_now():
    run_all_watchlists()
    return {"status": "done"}

frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")

app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    return FileResponse(os.path.join(frontend_dist, "index.html"))