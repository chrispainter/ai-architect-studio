from sqlalchemy.orm import Session
from . import models, schemas

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).offset(skip).limit(limit).all()

def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(title=project.title, description=project.description)
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
        security_standards=""
    )
    db.add(db_kb)
    db.commit()
    return db_project

def update_project_status(db: Session, project_id: int, status: str):
    db_project = get_project(db, project_id)
    if db_project:
        db_project.status = status
        db.commit()
        db.refresh(db_project)
    return db_project

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
        db_kb = models.KnowledgeBase(project_id=project_id, **kb.dict())
        db.add(db_kb)
        db.commit()
        db.refresh(db_kb)
    return db_kb

def create_requirement(db: Session, project_id: int, requirement: schemas.RequirementCreate):
    db_req = models.Requirement(project_id=project_id, content=requirement.content)
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return db_req

def get_requirements(db: Session, project_id: int):
    return db.query(models.Requirement).filter(models.Requirement.project_id == project_id).all()

def create_agent_output(db: Session, project_id: int, output: schemas.AgentOutputCreate):
    db_output = models.AgentOutput(project_id=project_id, **output.dict())
    db.add(db_output)
    db.commit()
    db.refresh(db_output)
    return db_output

def get_agent_outputs(db: Session, project_id: int):
    return db.query(models.AgentOutput).filter(models.AgentOutput.project_id == project_id).order_by(models.AgentOutput.created_at.asc()).all()
