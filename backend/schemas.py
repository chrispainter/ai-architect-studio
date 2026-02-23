from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# KnowledgeBase Schemas
class KnowledgeBaseBase(BaseModel):
    ux_guidelines: Optional[str] = None
    security_standards: Optional[str] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBase(KnowledgeBaseBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True

# Requirement Schemas
class RequirementBase(BaseModel):
    content: str

class RequirementCreate(RequirementBase):
    pass

class Requirement(RequirementBase):
    id: int
    project_id: int

    class Config:
        orm_mode = True

# AgentOutput Schemas
class AgentOutputBase(BaseModel):
    agent_name: str
    task_name: str
    output_content: str

class AgentOutputCreate(AgentOutputBase):
    pass

class AgentOutput(AgentOutputBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Project Schemas
class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    status: Optional[str] = None

class Project(ProjectBase):
    id: int
    status: str
    created_at: datetime
    knowledge_base: Optional[KnowledgeBase] = None
    requirements: List[Requirement] = []
    agent_outputs: List[AgentOutput] = []

    class Config:
        from_attributes = True
