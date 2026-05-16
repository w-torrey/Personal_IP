
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dork_engine import run_dork

app = FastAPI(
    title="IndexPulse API",
    description="OSINT Google Dork Monitoring Engine",
    version="0.1.0"
)

# Allow React frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class DorkRequest(BaseModel):
    person: str
    organization: str
    hours: Optional[int] = 24
    num_results: Optional[int] = 10


class DorkResponse(BaseModel):
    success: bool
    query: str
    person: str
    organization: str
    hours_back: int
    total_results: int
    fetched_at: str
    results: list


# --- Routes ---

@app.get("/")
def root():
    return {"status": "IndexPulse API is running"}


@app.post("/search", response_model=DorkResponse)
def search(request: DorkRequest):
    """
    Run a Google dork for a given person + organization.
    Returns structured results from the past N hours.
    """
    if not request.person or not request.organization:
        raise HTTPException(status_code=400, detail="person and organization are required")

    result = run_dork(
        person=request.person,
        organization=request.organization,
        hours=request.hours,
        num_results=request.num_results
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "SERP API call failed"))

    return result


@app.get("/search")
def search_get(
    person: str = Query(..., description="Full name of the person"),
    organization: str = Query(..., description="Organization name"),
    hours: int = Query(24, description="How far back to search in hours"),
    num_results: int = Query(10, description="Number of results to return")
):
    """
    GET version of /search for quick browser/curl testing.
    """
    result = run_dork(person=person, organization=organization, hours=hours, num_results=num_results)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "SERP API call failed"))

    return result