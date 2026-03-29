from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.models.db import Project
import secrets

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    repo_url: str | None = None


@router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "repo_url": p.repo_url,
            "created_at": p.created_at,
        }
        for p in projects
    ]


@router.post("/projects")
async def create_project(
    body: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
):
    slug = body.name.lower().replace(" ", "-")
    existing = await db.execute(select(Project).where(Project.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Project slug '{slug}' already exists")

    project = Project(
        name=body.name,
        slug=slug,
        description=body.description,
        repo_url=body.repo_url,
        api_key=f"nxr_{secrets.token_urlsafe(32)}",
    )
    db.add(project)
    await db.flush()

    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "api_key": project.api_key,
        "message": "Project created. Store the api_key securely — it won't be shown again.",
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
