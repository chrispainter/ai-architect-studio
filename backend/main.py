from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List

import crud, models, schemas, export
from auth import verify_password, create_access_token, get_current_user
from config import get_settings
from database import SessionLocal, engine, get_db
from websocket import manager

settings = get_settings()

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Architect Studio")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Health
# ============================================================

@app.get("/ping")
def ping():
    return {"status": "ok"}


# ============================================================
# Models — /api/v1/models
# ============================================================

AVAILABLE_MODELS = [
    {
        "value": "gemini-2.5-pro",
        "label": "Gemini 2.5 Pro",
        "description": "Recommended default. Stable, high-quality reasoning, reliable capacity.",
        "tier": "balanced",
    },
    {
        "value": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "description": "Faster and cheaper. Use for iteration or low-stakes runs. Lower reasoning ceiling.",
        "tier": "fast",
    },
    {
        "value": "gemini-3.1-pro-preview",
        "label": "Gemini 3.1 Pro (preview)",
        "description": "Best quality when available, but preview tier — frequently hits 503 capacity errors.",
        "tier": "experimental",
    },
    {
        "value": "gemini-3.1-flash-preview",
        "label": "Gemini 3.1 Flash (preview)",
        "description": "Newer fast model, preview tier. May also hit capacity issues.",
        "tier": "experimental",
    },
]


@app.get("/api/v1/models")
def list_models():
    from config import get_settings
    settings = get_settings()
    return {
        "default": settings.gemini_model,
        "models": AVAILABLE_MODELS,
    }


# ============================================================
# Auth — /api/v1/auth
# ============================================================

@app.post("/api/v1/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@app.post("/api/v1/auth/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/v1/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ============================================================
# Projects — /api/v1/projects
# ============================================================

@app.post("/api/v1/projects/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_project(db=db, project=project, user_id=current_user.id)


@app.get("/api/v1/projects/", response_model=List[schemas.Project])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_projects(db, user_id=current_user.id, skip=skip, limit=limit)


@app.get("/api/v1/projects/{project_id}", response_model=schemas.ProjectWithRuns)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = crud.get_project(db, project_id=project_id, user_id=current_user.id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project


@app.put("/api/v1/projects/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    updates: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = crud.update_project(db, project_id, updates, user_id=current_user.id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project


@app.delete("/api/v1/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    success = crud.delete_project(db, project_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted"}


# ============================================================
# Requirements — /api/v1/projects/{id}/requirements
# ============================================================

@app.post("/api/v1/projects/{project_id}/requirements/", response_model=schemas.Requirement)
def create_requirement(
    project_id: int,
    requirement: schemas.RequirementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = crud.get_project(db, project_id, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.create_requirement(db=db, project_id=project_id, requirement=requirement)


# ============================================================
# Knowledge Base — /api/v1/projects/{id}/knowledge_base
# ============================================================

@app.put("/api/v1/projects/{project_id}/knowledge_base/", response_model=schemas.KnowledgeBase)
def update_knowledge_base(
    project_id: int,
    kb: schemas.KnowledgeBaseBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = crud.get_project(db, project_id, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.update_knowledge_base(db=db, project_id=project_id, kb=kb)


# ============================================================
# Agent Outputs — /api/v1/projects/{id}/outputs
# ============================================================

@app.get("/api/v1/projects/{project_id}/outputs/", response_model=List[schemas.AgentOutput])
def get_outputs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = crud.get_project(db, project_id, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.get_agent_outputs(db=db, project_id=project_id)


# ============================================================
# Crew Runs — /api/v1/projects/{id}/runs
# ============================================================

@app.post("/api/v1/projects/{project_id}/runs", response_model=schemas.CrewRun)
def start_crew_run(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = crud.get_project(db, project_id, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if any run is already in progress for this project
    existing_runs = crud.get_crew_runs(db, project_id)
    for run in existing_runs:
        if run.status in ("queued", "running"):
            raise HTTPException(status_code=400, detail="A crew run is already in progress for this project")

    crew_run = crud.create_crew_run(db, project_id)
    crud.update_project_status(db, project_id, "running")

    import crew_runner
    background_tasks.add_task(crew_runner.run_crew_for_project, project_id, crew_run.id)
    return crew_run


@app.get("/api/v1/projects/{project_id}/runs", response_model=List[schemas.CrewRun])
def list_crew_runs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = crud.get_project(db, project_id, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.get_crew_runs(db, project_id)


@app.get("/api/v1/runs/{run_id}", response_model=schemas.CrewRun)
def get_crew_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_run = crud.get_crew_run(db, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
    # Verify ownership through project
    db_project = crud.get_project(db, db_run.project_id, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Run not found")
    return db_run


@app.get("/api/v1/runs/{run_id}/export")
def export_crew_run_markdown(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Download a crew run's outputs as a single, well-organized markdown
    document — suitable for handing off to a coding agent (Claude Code,
    Antigravity, etc.) as the initial project brief."""
    db_run = crud.get_crew_run(db, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
    db_project = crud.get_project(db, db_run.project_id, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Run not found")

    outputs = crud.get_agent_outputs_by_run(db, run_id)
    requirements = crud.get_requirements(db, db_project.id)
    markdown = export.render_run_markdown(db_project, db_run, outputs, requirements)
    filename = export.filename_for_run(db_project, db_run)

    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Expose Content-Disposition so the frontend can read the
            # server-suggested filename when downloading via fetch.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# ============================================================
# WebSocket — /ws/runs/{run_id}
# ============================================================

@app.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: int):
    await manager.connect(run_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)


# ============================================================
# Legacy Routes (backward compat — no auth required)
# These will be removed in a future release.
# ============================================================

@app.get("/projects/", response_model=List[schemas.Project])
def legacy_read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_projects(db, skip=skip, limit=limit)


@app.get("/projects/{project_id}", response_model=schemas.Project)
def legacy_read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project


@app.post("/projects/", response_model=schemas.Project)
def legacy_create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    return crud.create_project(db=db, project=project)


@app.post("/projects/{project_id}/requirements/", response_model=schemas.Requirement)
def legacy_create_requirement(project_id: int, requirement: schemas.RequirementCreate, db: Session = Depends(get_db)):
    return crud.create_requirement(db=db, project_id=project_id, requirement=requirement)


@app.put("/projects/{project_id}/knowledge_base/", response_model=schemas.KnowledgeBase)
def legacy_update_kb(project_id: int, kb: schemas.KnowledgeBaseBase, db: Session = Depends(get_db)):
    return crud.update_knowledge_base(db=db, project_id=project_id, kb=kb)


@app.get("/projects/{project_id}/outputs/", response_model=List[schemas.AgentOutput])
def legacy_get_outputs(project_id: int, db: Session = Depends(get_db)):
    return crud.get_agent_outputs(db=db, project_id=project_id)


@app.post("/projects/{project_id}/run", response_model=dict)
def legacy_run_crew(project_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    if db_project.status == "running":
        raise HTTPException(status_code=400, detail="Project is already running")
    crud.update_project_status(db, project_id, "starting")

    crew_run = crud.create_crew_run(db, project_id)

    import crew_runner
    background_tasks.add_task(crew_runner.run_crew_for_project, project_id, crew_run.id)
    return {"status": "accepted", "message": "Crew execution started in background.", "run_id": crew_run.id}
