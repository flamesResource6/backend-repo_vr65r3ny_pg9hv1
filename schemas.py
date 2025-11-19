"""
Database Schemas for Lee Willemse Portfolio

Each Pydantic model represents a collection in MongoDB. The collection name is the
lowercase of the class name (e.g., Project -> "project").

These schemas are used by the database helper and the admin UI.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

# Core profile and narrative
class Profile(BaseModel):
    name: str = Field(..., description="Full name")
    tagline: str = Field(..., description="Primary hero tagline")
    traits: List[str] = Field(default_factory=list, description="Rotating traits under the headline")
    about: str = Field("", description="About section copy")
    avatar_url: Optional[str] = Field(None, description="URL to profile picture")
    location: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    website: Optional[str] = Field(None)
    resume_url: Optional[str] = Field(None, description="Public URL to resume PDF")
    theme_preference: str = Field("system", description="light | dark | system")

# Projects
class Project(BaseModel):
    title: str
    description: str
    thumbnail_url: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    github_url: Optional[str] = None
    live_demo_url: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    challenges: List[str] = Field(default_factory=list)
    solutions: List[str] = Field(default_factory=list)
    year: Optional[int] = Field(None, description="Year built")

# Certificates
class Certificate(BaseModel):
    title: str
    organization: str
    date_awarded: date
    skill_category: str
    asset_url: Optional[str] = Field(None, description="Image/PDF public URL")
    reflection: str = Field("", description="What I learned from this")

# Learning journal
class JournalEntry(BaseModel):
    title: str
    content_markdown: str
    tags: List[str] = Field(default_factory=list)
    linked_project_title: Optional[str] = None
    linked_certificate_title: Optional[str] = None
    date_logged: date

# Skill snapshots over time (for evolution graphs)
class SkillSnapshot(BaseModel):
    date_captured: date
    skills: dict = Field(default_factory=dict, description="{ skillName: 0-100 score }")

# Timeline milestones for story mode
class Milestone(BaseModel):
    title: str
    description: str
    date_achieved: date
    kind: str = Field("general", description="start | challenge | win | launch | general")

# Notes:
# - The Flames database viewer can use these schemas automatically.
# - Your API can still aggregate across these collections for stats and AI responses.
