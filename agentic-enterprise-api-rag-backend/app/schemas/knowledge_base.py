from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    domain_type: str = Field(default="api", pattern="^(api|product|hr)$")
    is_active: bool = True


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    domain_type: str | None = Field(default=None, pattern="^(api|product|hr)$")
    is_active: bool | None = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    domain_type: str
    is_active: bool
    created_by: int | None
    created_at: str | None
