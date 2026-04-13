from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable for migration
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, running, completed, error
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="projects")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    knowledge_base = relationship("KnowledgeBase", back_populates="project", uselist=False, cascade="all, delete-orphan")
    agent_outputs = relationship("AgentOutput", back_populates="project", cascade="all, delete-orphan")
    crew_runs = relationship("CrewRun", back_populates="project", cascade="all, delete-orphan")


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    content = Column(Text)

    project = relationship("Project", back_populates="requirements")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    pm_guidelines = Column(Text, nullable=True)
    architect_guidelines = Column(Text, nullable=True)
    systems_guidelines = Column(Text, nullable=True)
    ai_guidelines = Column(Text, nullable=True)
    ux_guidelines = Column(Text, nullable=True)
    security_standards = Column(Text, nullable=True)

    project = relationship("Project", back_populates="knowledge_base")


class CrewRun(Base):
    __tablename__ = "crew_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    status = Column(String, default="queued")  # queued, running, completed, error
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    trigger_source = Column(String, default="manual")  # manual, n8n_webhook, scheduled

    project = relationship("Project", back_populates="crew_runs")
    agent_outputs = relationship("AgentOutput", back_populates="crew_run", cascade="all, delete-orphan")


class AgentOutput(Base):
    __tablename__ = "agent_outputs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    crew_run_id = Column(Integer, ForeignKey("crew_runs.id"), nullable=True)
    agent_name = Column(String)
    task_name = Column(String)
    output_content = Column(Text)
    artifact_type = Column(String, nullable=True)  # prd, adr, wireframe, security_audit, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="agent_outputs")
    crew_run = relationship("CrewRun", back_populates="agent_outputs")
