import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient

env_path = Path(__file__).resolve().parent / ".env"
print(f"DEBUG: Searching for .env at: {env_path}")
print(f"DEBUG: .env exists at that path: {env_path.exists()}")
load_dotenv(env_path, override=True)
print(f"DEBUG: MONGODB_URI found: {bool(os.getenv('MONGODB_URI'))}")
if not os.getenv("MONGODB_URI"):
    print("WARNING: MONGODB_URI is still not set after load_dotenv!")

app = FastAPI(
    title="Compass Travel API",
    version="1.0.0",
    openapi_tags=[
        {"name": "Health", "description": "Liveness and MongoDB connectivity."},
        {"name": "Trips", "description": "Trips, approvals, issues, policies."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mongo_client() -> MongoClient:
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        env_keys = list(os.environ.keys())
        # only show some keys for security, or just the length
        raise HTTPException(
            status_code=500,
            detail=f"Missing MONGODB_URI environment variable. Loaded keys: {len(env_keys)}. Search path: {env_path}",
        )
    return MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)


def _get_db():
    mongo_db_name = os.getenv("MONGODB_DB", "Compass")
    return _mongo_client()[mongo_db_name]


def _to_jsonable(doc: Any) -> Any:
    if isinstance(doc, dict):
        out = {}
        for key, value in doc.items():
            if key == "_id":
                out["id"] = str(value)
                continue
            out[key] = _to_jsonable(value)
        return out
    if isinstance(doc, list):
        return [_to_jsonable(item) for item in doc]
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc


def _find_trip_by_id(db, trip_id: str) -> Optional[Dict[str, Any]]:
    trip = db.trips.find_one({"id": trip_id})
    if trip:
        return trip
    if ObjectId.is_valid(trip_id):
        return db.trips.find_one({"_id": ObjectId(trip_id)})
    return None


class TripCreate(BaseModel):
    destination: str
    purpose: str
    traveler_name: str
    status: str = "planning"
    budget: float | int | str | None = None


class ApprovalCreate(BaseModel):
    tripId: str
    approver: str
    status: str = "pending"
    reason: str | None = None


class IssueCreate(BaseModel):
    tripId: str
    title: str
    description: str
    urgency: Literal["low", "medium", "high", "critical"] = "medium"
    status: str = "open"


class PolicyCreate(BaseModel):
    destination: str
    rules: List[str] = Field(default_factory=list)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "compass-travel-api"}


@app.get("/api/config-check", tags=["Health"])
def config_check():
    return {
        "mongodb_uri_set": bool(os.getenv("MONGODB_URI")),
        "mongodb_db": os.getenv("MONGODB_DB", "Compass"),
    }


@app.get("/api/mongo-check", tags=["Health"])
def mongo_check():
    try:
        client = _mongo_client()
        client.admin.command("ping")
        client.close()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MongoDB connection failed: {exc}") from exc
    return {"ok": True, "database": os.getenv("MONGODB_DB", "Compass")}


@app.post("/api/trips", tags=["Trips"])
def create_trip(payload: TripCreate):
    db = _get_db()
    data = payload.model_dump()
    inserted = db.trips.insert_one(data)
    doc = db.trips.find_one({"_id": inserted.inserted_id})
    return _to_jsonable(doc)


@app.get("/api/trips", tags=["Trips"])
def list_trips(status: str | None = Query(default=None), destination: str | None = Query(default=None)):
    db = _get_db()
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if destination:
        query["destination"] = destination
    docs = list(db.trips.find(query).sort("_id", -1).limit(100))
    return _to_jsonable(docs)


@app.get("/api/trips/{trip_id}", tags=["Trips"])
def get_trip(trip_id: str):
    db = _get_db()
    trip = _find_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip not found for id '{trip_id}'.")
    return _to_jsonable(trip)


@app.post("/api/approvals", tags=["Trips"])
def create_approval(payload: ApprovalCreate):
    db = _get_db()
    inserted = db.approvals.insert_one(payload.model_dump())
    doc = db.approvals.find_one({"_id": inserted.inserted_id})
    return _to_jsonable(doc)


@app.post("/api/issues", tags=["Trips"])
def create_issue(payload: IssueCreate):
    db = _get_db()
    inserted = db.issues.insert_one(payload.model_dump())
    doc = db.issues.find_one({"_id": inserted.inserted_id})
    return _to_jsonable(doc)


@app.post("/api/policies", tags=["Trips"])
def upsert_policy(payload: PolicyCreate):
    db = _get_db()
    db.policies.update_one({"destination": payload.destination}, {"$set": payload.model_dump()}, upsert=True)
    doc = db.policies.find_one({"destination": payload.destination})
    return _to_jsonable(doc)
