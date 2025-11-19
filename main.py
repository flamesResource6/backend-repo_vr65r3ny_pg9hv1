import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Profile, Project, Certificate, JournalEntry, SkillSnapshot, Milestone

app = FastAPI(title="Lee Willemse Portfolio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities
class Obj(BaseModel):
    id: str

def to_oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


def as_serializable(doc: Dict[str, Any]):
    if not doc:
        return doc
    d = dict(doc)
    if d.get("_id"):
        d["id"] = str(d.pop("_id"))
    # Convert datetimes to isoformat
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def coll_name(model_cls) -> str:
    return model_cls.__name__.lower()


@app.get("/")
def root():
    return {"message": "Lee Willemse Portfolio API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", None) or "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:20]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Generic CRUD helpers

def create_item(model: BaseModel):
    collection = coll_name(model.__class__)
    new_id = create_document(collection, model)
    doc = db[collection].find_one({"_id": ObjectId(new_id)})
    return as_serializable(doc)


def list_items(model_cls, limit: Optional[int] = None, filters: Dict[str, Any] = None):
    collection = coll_name(model_cls)
    docs = get_documents(collection, filters or {}, limit)
    return [as_serializable(d) for d in docs]


def update_item(model_cls, id_str: str, data: Dict[str, Any]):
    collection = coll_name(model_cls)
    res = db[collection].update_one({"_id": to_oid(id_str)}, {"$set": {**data, "updated_at": datetime.utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = db[collection].find_one({"_id": to_oid(id_str)})
    return as_serializable(doc)


def delete_item(model_cls, id_str: str):
    collection = coll_name(model_cls)
    res = db[collection].delete_one({"_id": to_oid(id_str)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


# Profile (single latest document used)
@app.get("/profile")
def get_profile():
    docs = list_items(Profile, limit=1)
    return docs[0] if docs else {}


@app.post("/profile")
def post_profile(profile: Profile):
    return create_item(profile)


@app.patch("/profile/{id}")
def patch_profile(id: str, updates: Dict[str, Any]):
    return update_item(Profile, id, updates)


# Projects
@app.get("/projects")
def get_projects(tag: Optional[str] = None, tech: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if tag:
        filt["highlights"] = {"$elemMatch": {"$regex": tag, "$options": "i"}}
    if tech:
        filt["tech_stack"] = {"$elemMatch": {"$regex": tech, "$options": "i"}}
    return list_items(Project, filters=filt)


@app.post("/projects")
def create_project(project: Project):
    return create_item(project)


@app.patch("/projects/{id}")
def update_project(id: str, updates: Dict[str, Any]):
    return update_item(Project, id, updates)


@app.delete("/projects/{id}")
def remove_project(id: str):
    return delete_item(Project, id)


# Certificates
@app.get("/certificates")
def get_certs(skill: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if skill:
        filt["skill_category"] = {"$regex": skill, "$options": "i"}
    return list_items(Certificate, filters=filt)


@app.post("/certificates")
def create_cert(cert: Certificate):
    return create_item(cert)


@app.patch("/certificates/{id}")
def update_cert(id: str, updates: Dict[str, Any]):
    return update_item(Certificate, id, updates)


@app.delete("/certificates/{id}")
def remove_cert(id: str):
    return delete_item(Certificate, id)


# Journal
@app.get("/journal")
def get_journal(tag: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if tag:
        filt["tags"] = {"$elemMatch": {"$regex": tag, "$options": "i"}}
    return list_items(JournalEntry, filters=filt)


@app.post("/journal")
def create_journal(entry: JournalEntry):
    return create_item(entry)


@app.patch("/journal/{id}")
def update_journal(id: str, updates: Dict[str, Any]):
    return update_item(JournalEntry, id, updates)


@app.delete("/journal/{id}")
def remove_journal(id: str):
    return delete_item(JournalEntry, id)


# Skill snapshots
@app.get("/skills/snapshots")
def get_skill_snapshots():
    return list_items(SkillSnapshot)


@app.post("/skills/snapshots")
def add_skill_snapshot(s: SkillSnapshot):
    return create_item(s)


# Milestones
@app.get("/milestones")
def get_milestones():
    return list_items(Milestone)


@app.post("/milestones")
def add_milestone(m: Milestone):
    return create_item(m)


# Stats for recruiter mode
@app.get("/stats")
def get_stats():
    projects = db[coll_name(Project)].count_documents({}) if db else 0
    certs = db[coll_name(Certificate)].count_documents({}) if db else 0
    journal = db[coll_name(JournalEntry)].count_documents({}) if db else 0
    latest_snapshot = db[coll_name(SkillSnapshot)].find_one(sort=[("date_captured", -1)]) if db else None
    skills_mastered = len(latest_snapshot.get("skills", {})) if latest_snapshot else 0
    return {
        "total_projects": projects,
        "total_certificates": certs,
        "total_journal_entries": journal,
        "skills_mastered": skills_mastered,
    }


# Simple AI-style query (keyword + ranking) - no external LLM required
class AIQuery(BaseModel):
    question: str
    focus: Optional[str] = None  # "projects" | "certificates" | "journal"


@app.post("/ai/query")
def ai_query(payload: AIQuery):
    q = (payload.question or "").lower()
    focus = (payload.focus or "").lower()

    def rank_text(text: str) -> int:
        score = 0
        for token in q.split():
            if token and token in text.lower():
                score += 1
        return score

    results: Dict[str, List[Dict[str, Any]]] = {}

    # Projects
    if focus in ("", "project", "projects"):
        docs = list(db[coll_name(Project)].find()) if db else []
        ranked = sorted(
            [as_serializable(d) for d in docs],
            key=lambda d: rank_text(" ".join([
                d.get("title", ""),
                d.get("description", ""),
                " ".join(d.get("tech_stack", [])),
                " ".join(d.get("highlights", [])),
            ])),
            reverse=True,
        )
        results["projects"] = ranked[:5]

    # Certificates
    if focus in ("", "certificate", "certificates"):
        docs = list(db[coll_name(Certificate)].find()) if db else []
        ranked = sorted(
            [as_serializable(d) for d in docs],
            key=lambda d: rank_text(" ".join([
                d.get("title", ""), d.get("organization", ""), d.get("skill_category", ""), d.get("reflection", "")
            ])),
            reverse=True,
        )
        results["certificates"] = ranked[:5]

    # Journal
    if focus in ("", "journal"):
        docs = list(db[coll_name(JournalEntry)].find()) if db else []
        ranked = sorted(
            [as_serializable(d) for d in docs],
            key=lambda d: rank_text(" ".join([
                d.get("title", ""), d.get("content_markdown", ""), " ".join(d.get("tags", []))
            ])),
            reverse=True,
        )
        results["journal"] = ranked[:5]

    # Lightweight narrative summary
    summary = ""
    if results.get("projects"):
        top = results["projects"][0]
        summary += f"Top project: {top.get('title')} — tech: {', '.join(top.get('tech_stack', []))}. "
    if results.get("certificates"):
        topc = results["certificates"][0]
        summary += f"Recent certificate: {topc.get('title')} in {topc.get('skill_category')}. "
    if results.get("journal"):
        topj = results["journal"][0]
        summary += f"Learning focus: {', '.join(topj.get('tags', [])[:3])}."

    return {"answer": summary.strip(), "results": results}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
