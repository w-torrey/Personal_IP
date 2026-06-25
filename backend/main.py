from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from dork_engine import run_dork
from database import save_results, get_or_create_watchlist, get_new_alerts, get_all_watchlists, delete_watchlist_db, create_user, get_user_by_email
from scheduler import start_scheduler, stop_scheduler, run_all_watchlists
import auth
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler(interval_hours=24)
    yield
    stop_scheduler()

app = FastAPI(
    title="IndexPulse API",
    description="OSINT Google Dork Monitoring Engine",
    version="0.3.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://100.65.81.57:8000",
        "http://10.0.0.214:8000",
        "http://indexpulse-server:8000",
        "http://indexpulse-server.local:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DorkRequest(BaseModel):
    label: Optional[str] = None
    keywords: Optional[list[str]] = None
    include_sites: Optional[list[str]] = None
    exclude_sites: Optional[list[str]] = None
    hours: Optional[int] = 24
    num_results: Optional[int] = 10
    category: Optional[str] = "Uncategorized"

def validate_request(request: DorkRequest):
    if not any([request.keywords, request.include_sites]):
        raise HTTPException(
            status_code=400,
            detail="At least one of: keywords or include_sites is required."
        )

def resolve_label(request: DorkRequest) -> str:
    if request.label:
        return request.label
    if request.keywords:
        return ", ".join(request.keywords)
    return "Unnamed Watchlist"

@app.post("/search")
def search(request: DorkRequest):
    validate_request(request)
    result = run_dork(
        keywords=request.keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        hours=request.hours,
        num_results=request.num_results,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "SerpApi call failed"))
    return result

@app.post("/monitor")
def monitor(request: DorkRequest):
    validate_request(request)
    label = resolve_label(request)
    watchlist_id = get_or_create_watchlist(
        label=label,
        keywords=request.keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        category=request.category,
    )
    result = run_dork(
        keywords=request.keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        hours=request.hours,
        num_results=request.num_results,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "SerpApi call failed"))
    saved = save_results(watchlist_id, result["results"])
    return {"watchlist_id": watchlist_id, "query": result["query"], "results": result["results"], "db": saved}

@app.get("/alerts")
def alerts():
    return get_new_alerts()

@app.get("/watchlists")
def get_watchlists():
    return get_all_watchlists()

@app.post("/watchlist")
def create_watchlist(request: DorkRequest):
    validate_request(request)
    label = resolve_label(request)
    watchlist_id = get_or_create_watchlist(
        label=label,
        keywords=request.keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        category=request.category,
    )
    return {"watchlist_id": watchlist_id, "label": label, "category": request.category}

@app.post("/run-now")
def run_now():
    run_all_watchlists()
    return {"status": "done"}

frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.put("/watchlist/{watchlist_id}")
def update_watchlist(watchlist_id: int, request: DorkRequest):
    from database import update_watchlist as db_update_watchlist
    label = resolve_label(request)
    db_update_watchlist(
        watchlist_id=watchlist_id,
        label=label,
        keywords=request.keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        category=request.category,
    )
    return {"watchlist_id": watchlist_id, "label": label, "category": request.category}

class AuthRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/register")
def register(request: AuthRequest):
    if get_user_by_email(request.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = auth.hash_password(request.password)
    create_user(request.email, hashed)
    return {"message": "Account created"}

@app.post("/auth/login")
def login(request: AuthRequest):
    user = get_user_by_email(request.email)
    if not user or not auth.verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_access_token(user["email"])
    return {"token": token, "email": user["email"]}


@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.delete("/watchlist/{watchlist_id}")
def delete_watchlist(watchlist_id:int):
    deleted = delete_watchlist_db(watchlist_id)
    if not deleted: raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"deleted": watchlist_id}