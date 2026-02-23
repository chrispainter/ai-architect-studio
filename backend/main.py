from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from . import crud, models, schemas
from .database import SessionLocal, engine, get_db

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Architect Studio - Intake Engine")

# Add CORS middleware to allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    return crud.create_project(db=db, project=project)

@app.get("/projects/", response_model=List[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_projects(db, skip=skip, limit=limit)

@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.post("/projects/{project_id}/requirements/", response_model=schemas.Requirement)
def create_requirement_for_project(
    project_id: int, requirement: schemas.RequirementCreate, db: Session = Depends(get_db)
):
    return crud.create_requirement(db=db, project_id=project_id, requirement=requirement)

@app.put("/projects/{project_id}/knowledge_base/", response_model=schemas.KnowledgeBase)
def update_kb_for_project(
    project_id: int, kb: schemas.KnowledgeBaseBase, db: Session = Depends(get_db)
):
    return crud.update_knowledge_base(db=db, project_id=project_id, kb=kb)

@app.get("/projects/{project_id}/outputs/", response_model=List[schemas.AgentOutput])
def get_outputs_for_project(project_id: int, db: Session = Depends(get_db)):
    return crud.get_agent_outputs(db=db, project_id=project_id)

from . import crew_runner

@app.post("/projects/{project_id}/run", response_model=dict)
def run_project_crew(project_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if db_project.status == "running":
        raise HTTPException(status_code=400, detail="Project is already running")
        
    crud.update_project_status(db, project_id, "starting")
    background_tasks.add_task(crew_runner.run_crew_for_project, project_id)
    return {"status": "accepted", "message": "Crew execution started in background."}

