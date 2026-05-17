from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dork_engine import run_dork
from database import save_results, get_or_create_watchlist, get_new_alerts

app = FastAPI(
    title="IndexPulse API",
    description="OSINT Google Dork Monitoring Engine",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DorkRequest(BaseModel):
    person: str
    organization: str
    hours: Optional[int] = 24
    num_results: Optional[int] = 10

@app.get("/")
def root():
    return {"status": "IndexPulse is running"}

@app.get("/search")
def search(
    person: str = Query(...),
    organization: str = Query(...),
    hours: int = Query(24),
    num_results: int = Query(10)
):
    result = run_dork(person=person, organization=organization, hours=hours, num_results=num_results)
    if not result["success"]:
        raise HTTPException(status_code=500, detail="SerpApi call failed")
    return result

@app.post("/monitor")
def monitor(request: DorkRequest):
    """Runs a dork and saves results to the database."""
    watchlist_id = get_or_create_watchlist(request.person, request.organization)
    result = run_dork(request.person, request.organization, request.hours, request.num_results)
    if not result["success"]:
        raise HTTPException(status_code=500, detail="SerpApi call failed")
    saved = save_results(watchlist_id, result["results"])
    return {"watchlist_id": watchlist_id, "results": result["results"], "db": saved}

@app.get("/alerts")
def alerts():
    """Returns all new unseen alerts from the database."""
    return get_new_alerts()