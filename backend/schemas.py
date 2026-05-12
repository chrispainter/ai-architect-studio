from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


# --- Auth Schemas ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- KnowledgeBase Schemas ---

class KnowledgeBaseBase(BaseModel):
    pm_guidelines: Optional[str] = None
    architect_guidelines: Optional[str] = None
    systems_guidelines: Optional[str] = None
    ai_guidelines: Optional[str] = None
    ux_guidelines: Optional[str] = None
    security_standards: Optional[str] = None


class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass


class KnowledgeBase(KnowledgeBaseBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True


# --- Requirement Schemas ---

class RequirementBase(BaseModel):
    content: str


class RequirementCreate(RequirementBase):
    pass


class Requirement(RequirementBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True


# --- AgentOutput Schemas ---

class AgentOutputBase(BaseModel):
    agent_name: str
    task_name: str
    output_content: str
    artifact_type: Optional[str] = None


class AgentOutputCreate(AgentOutputBase):
    pass


class AgentOutput(AgentOutputBase):
    id: int
    project_id: int
    crew_run_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- CrewRun Schemas ---

class CrewRunCreate(BaseModel):
    trigger_source: str = "manual"


class CrewRun(BaseModel):
    id: int
    project_id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    trigger_source: str
    agent_outputs: List[AgentOutput] = []

    class Config:
        from_attributes = True


# --- Project Schemas ---

class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    github_url: Optional[str] = None
    discovery_enabled: bool = True
    llm_model: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    github_url: Optional[str] = None
    status: Optional[str] = None
    discovery_enabled: Optional[bool] = None
    llm_model: Optional[str] = None


class Project(ProjectBase):
    id: int
    status: str
    created_at: datetime
    knowledge_base: Optional[KnowledgeBase] = None
    requirements: List[Requirement] = []
    agent_outputs: List[AgentOutput] = []

    class Config:
        from_attributes = True


class ProjectWithRuns(Project):
    crew_runs: List[CrewRun] = []

    class Config:
        from_attributes = True
