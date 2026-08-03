from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from dork_engine import run_dork
from database import (
    save_results,
    get_or_create_watchlist,
    get_alerts,
    get_all_watchlists,
    db_update_watchlist,
    delete_watchlist_db,
    create_user,
    get_user_by_email,
    mark_as_read,
    get_digests,
    get_dossiers,
)
from scheduler import start_scheduler, stop_scheduler, run_all_watchlists
import auth
import os


@asynccontextmanager  # lifetime manager (found through)
async def lifespan(app: FastAPI):
    start_scheduler(interval_hours=24)
    yield  # above just start the scheduler and below stop it
    stop_scheduler()


# fast apit documentations title
app = FastAPI(
    title="IndexPulse API",
    description="OSINT Google Dork Monitoring Engine",
    version="0.3.0",
    lifespan=lifespan,
)

# allow thesecross origin resource sharing middlware
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


# take in information / query and allow API to manage as well
# just need a class
class DorkRequest(BaseModel):
    # all are optional for now
    label: Optional[str] = None
    keywords: Optional[list[str]] = None
    or_keywords: Optional[list[str]] = None
    exclude_keywords: Optional[list[str]] = None
    include_sites: Optional[list[str]] = None
    exclude_sites: Optional[list[str]] = None
    hours: Optional[int] = 24
    num_results: Optional[int] = 10
    category: Optional[str] = "Uncategorized"


# check if everything from keywords and include sites is actual there
# if there isnt at least one of them then it will raise 400
def validate_request(request: DorkRequest):
    if not any([request.keywords, request.include_sites]):
        raise HTTPException(
            status_code=400,
            detail="At least one of: keywords or include_sites is required.",
        )


# if there is no label then make one here
def resolve_label(request: DorkRequest) -> str:
    # if there is already a label then just move on
    if request.label:
        return request.label
    # no label
    if request.keywords:
        # joining keyword to make a label
        return ", ".join(request.keywords)
    return "Unnamed Watchlist"


# routes


# short search
@app.post("/search")
def search(request: DorkRequest, user: str = Depends(auth.get_current_user)):
    # validates
    validate_request(request)
    # run dork through dork engine
    result = run_dork(
        keywords=request.keywords,
        or_keywords=request.or_keywords,
        exclude_keywords=request.exclude_keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        hours=request.hours,
        num_results=request.num_results,
    )
    # check
    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result.get("error", "SerpApi call failed")
        )
    return result


# creates or finds a watchlist and runs and saves it
@app.post("/monitor")
def monitor(request: DorkRequest, user: str = Depends(auth.get_current_user)):
    validate_request(request)
    label = resolve_label(request)
    # db create new id if needed
    # check with dork engine for completion
    watchlist_id = get_or_create_watchlist(
        label=label,
        keywords=request.keywords,
        or_keywords=request.or_keywords,
        exclude_keywords=request.exclude_keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        category=request.category,
    )
    # once created then run dork
    result = run_dork(
        keywords=request.keywords,
        or_keywords=request.or_keywords,
        exclude_keywords=request.exclude_keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        hours=request.hours,
        num_results=request.num_results,
    )
    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result.get("error", "SerpApi call failed")
        )  # all checks in API
    saved = save_results(watchlist_id, result["results"])
    return {
        "watchlist_id": watchlist_id,
        "query": result["query"],
        "results": result["results"],
        "db": saved,
    }


# checks alerts
@app.get("/alerts")
def alerts(user: str = Depends(auth.get_current_user)):
    return get_alerts()


# read recipt endpoint
@app.patch("/alerts/{alert_id}/read")
def read(alert_id: int, user: str = Depends(auth.get_current_user)):
    updated = mark_as_read(alert_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"id": alert_id, "is_read": True}


# uses the get watchlists from db
@app.get("/watchlists")
def get_watchlists(user: str = Depends(auth.get_current_user)):
    return get_all_watchlists()


# creates a watchlist
@app.post("/watchlist")
def create_watchlist(request: DorkRequest, user: str = Depends(auth.get_current_user)):
    validate_request(request)
    label = resolve_label(request)
    watchlist_id = get_or_create_watchlist(
        label=label,
        keywords=request.keywords,
        or_keywords=request.or_keywords,
        exclude_keywords=request.exclude_keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        category=request.category,
    )
    return {"watchlist_id": watchlist_id, "label": label, "category": request.category}


# run all watchlists mainly for testing purposes
@app.post("/run-now")
def run_now(user: str = Depends(auth.get_current_user)):
    run_all_watchlists()
    return {"status": "done"}


# serve frontend (this came from claude)
frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(frontend_dist, "assets")),
    name="assets",
)


# serves digests
@app.get("/digests")
def digests(user: str = Depends(auth.get_current_user)):
    return get_digests()


# serves dossiers
@app.get("/dossiers")
def dossiers(user: str = Depends(auth.get_current_user)):
    return get_dossiers()


# in conjuction with above
@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    return FileResponse(os.path.join(frontend_dist, "index.html"))


# if you want to edit the watchlist (hence the put request)
@app.put("/watchlist/{watchlist_id}")
def update_watchlist(
    watchlist_id: int, request: DorkRequest, user: str = Depends(auth.get_current_user)
):
    label = resolve_label(request)
    updated = db_update_watchlist(
        watchlist_id=watchlist_id,
        label=label,
        keywords=request.keywords,
        or_keywords=request.or_keywords,
        exclude_keywords=request.exclude_keywords,
        include_sites=request.include_sites,
        exclude_sites=request.exclude_sites,
        category=request.category,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"watchlist_id": watchlist_id, "label": label, "category": request.category}


# decleration of username and password
class AuthRequest(BaseModel):
    email: str
    password: str


# create user, hashes password
@app.post("/auth/register")
def register(request: AuthRequest):
    if "@" not in request.email or "." not in request.email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Invalid email")
    if get_user_by_email(request.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = auth.hash_password(request.password)
    create_user(request.email, hashed)
    return {"message": "Account created"}


# login, checks username and password
@app.post("/auth/login")
def login(request: AuthRequest):
    user = get_user_by_email(request.email)
    if not user or not auth.verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_access_token(user["email"])
    return {"token": token, "email": user["email"]}


# Delete wathchlist endpoint
@app.delete("/watchlist/{watchlist_id}")
def delete_watchlist(watchlist_id: int, user: str = Depends(auth.get_current_user)):
    deleted = delete_watchlist_db(watchlist_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"deleted": watchlist_id}
