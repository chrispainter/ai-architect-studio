from datetime import datetime, timezone
from sqlalchemy.orm import Session
import models, schemas
from auth import hash_password


# --- User CRUD ---

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        email=user.email,
        hashed_password=hash_password(user.password),
        full_name=user.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


# --- Project CRUD ---

def get_project(db: Session, project_id: int, user_id: int | None = None):
    query = db.query(models.Project).filter(models.Project.id == project_id)
    if user_id is not None:
        query = query.filter(models.Project.user_id == user_id)
    return query.first()


def get_projects(db: Session, user_id: int | None = None, skip: int = 0, limit: int = 100):
    query = db.query(models.Project)
    if user_id is not None:
        query = query.filter(models.Project.user_id == user_id)
    return query.order_by(models.Project.created_at.desc()).offset(skip).limit(limit).all()


def create_project(db: Session, project: schemas.ProjectCreate, user_id: int | None = None):
    db_project = models.Project(
        title=project.title,
        description=project.description,
        github_url=project.github_url,
        user_id=user_id,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # Initialize an empty knowledge base
    db_kb = models.KnowledgeBase(
        project_id=db_project.id,
        pm_guidelines="",
        architect_guidelines="",
        systems_guidelines="",
        ai_guidelines="",
        ux_guidelines="",
        security_standards="",
    )
    db.add(db_kb)
    db.commit()
    return db_project


def update_project(db: Session, project_id: int, updates: schemas.ProjectUpdate, user_id: int | None = None):
    db_project = get_project(db, project_id, user_id)
    if not db_project:
        return None
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, project_id: int, user_id: int | None = None) -> bool:
    db_project = get_project(db, project_id, user_id)
    if not db_project:
        return False
    db.delete(db_project)
    db.commit()
    return True


def update_project_status(db: Session, project_id: int, status: str):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project:
        db_project.status = status
        db.commit()
        db.refresh(db_project)
    return db_project


# --- Knowledge Base CRUD ---

def get_knowledge_base(db: Session, project_id: int):
    return db.query(models.KnowledgeBase).filter(models.KnowledgeBase.project_id == project_id).first()


def update_knowledge_base(db: Session, project_id: int, kb: schemas.KnowledgeBaseBase):
    db_kb = get_knowledge_base(db, project_id)
    if db_kb:
        db_kb.pm_guidelines = kb.pm_guidelines
        db_kb.architect_guidelines = kb.architect_guidelines
        db_kb.systems_guidelines = kb.systems_guidelines
        db_kb.ai_guidelines = kb.ai_guidelines
        db_kb.ux_guidelines = kb.ux_guidelines
        db_kb.security_standards = kb.security_standards
        db.commit()
        db.refresh(db_kb)
    else:
        db_kb = models.KnowledgeBase(project_id=project_id, **kb.model_dump())
        db.add(db_kb)
        db.commit()
        db.refresh(db_kb)
    return db_kb


# --- Requirement CRUD ---

def create_requirement(db: Session, project_id: int, requirement: schemas.RequirementCreate):
    db_req = models.Requirement(project_id=project_id, content=requirement.content)
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return db_req


def get_requirements(db: Session, project_id: int):
    return db.query(models.Requirement).filter(models.Requirement.project_id == project_id).all()


# --- CrewRun CRUD ---

def create_crew_run(db: Session, project_id: int, trigger_source: str = "manual") -> models.CrewRun:
    db_run = models.CrewRun(
        project_id=project_id,
        status="queued",
        trigger_source=trigger_source,
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


def update_crew_run_status(db: Session, run_id: int, status: str, error_message: str | None = None):
    db_run = db.query(models.CrewRun).filter(models.CrewRun.id == run_id).first()
    if db_run:
        db_run.status = status
        if status == "running" and not db_run.started_at:
            db_run.started_at = datetime.now(timezone.utc)
        if status in ("completed", "error"):
            db_run.completed_at = datetime.now(timezone.utc)
        if error_message:
            db_run.error_message = error_message
        db.commit()
        db.refresh(db_run)
    return db_run


def get_crew_run(db: Session, run_id: int):
    return db.query(models.CrewRun).filter(models.CrewRun.id == run_id).first()


def get_crew_runs(db: Session, project_id: int):
    return (
        db.query(models.CrewRun)
        .filter(models.CrewRun.project_id == project_id)
        .order_by(models.CrewRun.id.desc())
        .all()
    )


# --- AgentOutput CRUD ---

def create_agent_output(db: Session, project_id: int, output: schemas.AgentOutputCreate, crew_run_id: int | None = None):
    db_output = models.AgentOutput(
        project_id=project_id,
        crew_run_id=crew_run_id,
        **output.model_dump(),
    )
    db.add(db_output)
    db.commit()
    db.refresh(db_output)
    return db_output


def get_agent_outputs(db: Session, project_id: int):
    return (
        db.query(models.AgentOutput)
        .filter(models.AgentOutput.project_id == project_id)
        .order_by(models.AgentOutput.created_at.asc())
        .all()
    )


def get_agent_outputs_by_run(db: Session, run_id: int):
    return (
        db.query(models.AgentOutput)
        .filter(models.AgentOutput.crew_run_id == run_id)
        .order_by(models.AgentOutput.created_at.asc())
        .all()
    )
