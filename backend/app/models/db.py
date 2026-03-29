from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, JSON, ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id          = Column(String, primary_key=True, default=gen_uuid)
    name        = Column(String, nullable=False)
    slug        = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    repo_url    = Column(String, nullable=True)
    api_key     = Column(String, unique=True, default=gen_uuid)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    runs        = relationship("Run", back_populates="project", cascade="all, delete-orphan")
    kpis        = relationship("CustomKPI", back_populates="project", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id              = Column(String, primary_key=True, default=gen_uuid)
    project_id      = Column(String, ForeignKey("projects.id"), nullable=False)
    tool            = Column(String, nullable=False)
    tool_version    = Column(String, nullable=True)
    branch          = Column(String, nullable=True)
    commit_sha      = Column(String, nullable=True)
    commit_message  = Column(String, nullable=True)
    pr_number       = Column(String, nullable=True)
    environment     = Column(String, nullable=True)
    ci_provider     = Column(String, nullable=True)
    ci_run_url      = Column(String, nullable=True)
    triggered_by    = Column(String, nullable=True)
    started_at      = Column(DateTime, default=datetime.utcnow)
    finished_at     = Column(DateTime, nullable=True)
    duration_ms     = Column(Integer, default=0)
    total           = Column(Integer, default=0)
    passed          = Column(Integer, default=0)
    failed          = Column(Integer, default=0)
    skipped         = Column(Integer, default=0)
    flaky           = Column(Integer, default=0)
    pass_rate       = Column(Float, default=0.0)
    run_metadata    = Column(JSON, default=dict)

    project         = relationship("Project", back_populates="runs")
    test_results    = relationship("TestResult", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_runs_project_started", "project_id", "started_at"),
    )


class TestResult(Base):
    __tablename__ = "test_results"

    id              = Column(String, primary_key=True, default=gen_uuid)
    run_id          = Column(String, ForeignKey("runs.id"), nullable=False)
    project_id      = Column(String, nullable=False)   # denormalized for fast queries
    name            = Column(String, nullable=False)
    suite           = Column(String, nullable=False)
    file_path       = Column(String, nullable=True)
    status          = Column(String, nullable=False)
    duration_ms     = Column(Integer, default=0)
    started_at      = Column(DateTime, nullable=True)
    error_message   = Column(Text, nullable=True)
    stack_trace     = Column(Text, nullable=True)
    ai_category     = Column(String, nullable=True)
    ai_root_cause   = Column(Text, nullable=True)
    ai_fix          = Column(Text, nullable=True)
    ai_confidence   = Column(Float, nullable=True)
    flaky_score     = Column(Float, nullable=True)
    retry_count     = Column(Integer, default=0)
    browser         = Column(String, nullable=True)
    platform        = Column(String, nullable=True)
    device          = Column(String, nullable=True)
    screenshot_url  = Column(String, nullable=True)
    video_url       = Column(String, nullable=True)
    trace_url       = Column(String, nullable=True)
    tags            = Column(JSON, default=list)
    steps           = Column(JSON, default=list)
    result_metadata = Column(JSON, default=dict)

    run             = relationship("Run", back_populates="test_results")
    comments        = relationship("Comment", back_populates="test_result", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_results_run_id",      "run_id"),
        Index("ix_results_project_name","project_id", "name"),
        Index("ix_results_status",      "status"),
        Index("ix_results_flaky_score", "flaky_score"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id             = Column(String, primary_key=True, default=gen_uuid)
    test_result_id = Column(String, ForeignKey("test_results.id"), nullable=False)
    author         = Column(String, nullable=False)
    body           = Column(Text, nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    test_result    = relationship("TestResult", back_populates="comments")


class CustomKPI(Base):
    __tablename__ = "custom_kpis"

    id          = Column(String, primary_key=True, default=gen_uuid)
    project_id  = Column(String, ForeignKey("projects.id"), nullable=False)
    name        = Column(String, nullable=False)
    formula     = Column(Text, nullable=False)   # e.g. "passed / total * 100"
    threshold   = Column(Float, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    project     = relationship("Project", back_populates="kpis")


class User(Base):
    __tablename__ = "users"

    id            = Column(String, primary_key=True, default=gen_uuid)
    email         = Column(String, unique=True, nullable=False)
    name          = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role          = Column(String, default="member")   # "admin", "member", "viewer"
    created_at    = Column(DateTime, default=datetime.utcnow)
