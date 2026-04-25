"""DeerTeamX API Schemas - Pydantic models for request/response validation

All schemas strictly align with API_REFERENCE.md definitions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Authentication Schemas
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request schema."""
    
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 characters)")
    email: Optional[str] = Field(None, description="Email address (optional)")


class LoginRequest(BaseModel):
    """User login request schema."""
    
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class RoleUpdateRequest(BaseModel):
    """Role type update request schema."""
    
    role_type: str = Field(..., pattern="^(developer|researcher|enthusiast)$", description="Target role type")


class TokenResponse(BaseModel):
    """Authentication token response schema."""
    
    access_token: str
    refresh_token: str
    user: "UserInfo"


class UserInfo(BaseModel):
    """User information schema."""
    
    id: UUID
    username: str
    role_type: str
    created_at: datetime


# ============================================================================
# Permission Schemas
# ============================================================================

class PermissionMatrixResponse(BaseModel):
    """Permission matrix response schema."""
    
    role_type: str
    permissions: Dict[str, Dict[str, bool]]


# ============================================================================
# Team Configuration Schemas
# ============================================================================

class RoleConfig(BaseModel):
    """Role configuration schema."""
    
    role_id: str
    agent_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r'^[a-z0-9-]+$',
        description="Agent name (lowercase + hyphens only, e.g., 'code-scanner-v1')"
    )
    name: str
    goal: str
    backstory: Optional[str] = None
    soul_content: Optional[str] = Field(
        None,
        description="SOUL.md content defining agent personality and behavior guidelines"
    )
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    tool_groups: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    memory_enabled: Optional[bool] = False
    verbose: Optional[bool] = False
    allow_delegation: Optional[bool] = False
    max_iter: Optional[int] = Field(25, gt=0)
    max_retry_limit: Optional[int] = Field(2, ge=0)


class TaskConfig(BaseModel):
    """Task configuration schema."""
    
    task_id: str
    description: str
    expected_output: str
    assigned_role: str  # References role_id
    dependencies: List[str] = Field(default_factory=list)
    dynamic_trigger: Optional["DynamicTriggerConfig"] = None


class DynamicTriggerConfig(BaseModel):
    """Dynamic trigger configuration schema."""
    
    type: str = Field(..., pattern="^(output_contains|error_occurred|confidence_low|custom_llm_call)$")
    condition_value: Any  # string | string[] | number
    dynamic_agent_name: str


class GlobalSettings(BaseModel):
    """Global team settings schema."""
    
    process_type: str = Field(..., pattern="^(sequential|hierarchical|consensus)$")
    verbose: Optional[bool] = False
    manager_llm_model: Optional[str] = None
    manager_agent_id: Optional[str] = None
    crew_memory_enabled: Optional[bool] = False
    max_rpm: Optional[int] = Field(None, gt=0)
    cache_enabled: Optional[bool] = True
    long_term_memory_enabled: Optional[bool] = False
    share_crew: Optional[bool] = False
    state_persistence: Optional[bool] = False
    human_feedback_enabled: Optional[bool] = False


class CreateTeamRequest(BaseModel):
    """Team creation request schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    execution_mode: str = Field(..., pattern="^(static|hybrid)$")
    roles: List[RoleConfig]
    tasks: List[TaskConfig]
    global_settings: GlobalSettings


class UpdateTeamRequest(BaseModel):
    """Team update request schema (partial)."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    execution_mode: Optional[str] = None
    roles: Optional[List[RoleConfig]] = None
    tasks: Optional[List[TaskConfig]] = None
    global_settings: Optional[GlobalSettings] = None
    version: Optional[str] = None  # Optimistic lock version


class TeamSummary(BaseModel):
    """Team summary schema (for list views)."""
    
    team_id: str
    name: str
    execution_mode: str
    status: str
    creator_name: str
    create_time: datetime
    update_time: datetime
    latest_execution: Optional["ExecutionSummary"] = None


class TeamDetail(BaseModel):
    """Full team detail schema."""
    
    team_id: str
    name: str
    description: Optional[str]
    execution_mode: str
    version: str
    current_version_number: int
    status: str
    roles: List[RoleConfig]
    tasks: List[TaskConfig]
    global_settings: GlobalSettings
    creator_id: UUID
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    """Team list response schema with pagination."""
    
    teams: List[TeamSummary]
    pagination: "PaginationInfo"


class NameAvailabilityResponse(BaseModel):
    """Team name availability check response."""
    
    available: bool
    suggested_name: Optional[str] = None


# ============================================================================
# Execution Schemas
# ============================================================================

class TriggerExecutionRequest(BaseModel):
    """Execution trigger request schema."""
    
    team_id: str
    input_data: Dict[str, Any]


class ExecutionSummary(BaseModel):
    """Execution summary schema."""
    
    execution_id: str
    status: str
    token_stats: Optional["TokenStats"] = None


class TokenStats(BaseModel):
    """Token consumption statistics schema."""
    
    total_input_tokens: int
    total_output_tokens: int
    total_cost_cents: int


class ExecutionDetail(BaseModel):
    """Full execution detail schema."""
    
    execution_id: str
    team_id: str
    thread_id: str
    status: str
    progress: Optional["ExecutionProgress"] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    execution_order: Optional[List[str]] = None
    token_stats: Optional[TokenStats] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExecutionProgress(BaseModel):
    """Execution progress tracking schema."""
    
    current_node: Optional[str] = None
    completed_nodes: List[str] = Field(default_factory=list)
    total_nodes: int


class ExecutionListResponse(BaseModel):
    """Execution list response schema."""
    
    executions: List[ExecutionDetail]
    pagination: "PaginationInfo"


# ============================================================================
# Template Schemas
# ============================================================================

class CreateTemplateRequest(BaseModel):
    """Template creation request schema."""
    
    team_id: str
    template_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scope: str = Field(..., pattern="^(personal|system)$")


class TemplateSummary(BaseModel):
    """Template summary schema."""
    
    template_id: str
    template_name: str
    description: Optional[str]
    scope: str
    usage_count: int
    creator_name: str


class UseTemplateRequest(BaseModel):
    """Template usage request schema."""
    
    team_name: str
    overrides: Optional[Dict[str, Any]] = None


# ============================================================================
# CrewAI Import Schemas
# ============================================================================

class ImportTaskStatus(BaseModel):
    """Import task status schema."""
    
    task_id: str
    status: str  # pending/processing/completed/failed/cancelled
    progress: int = Field(ge=0, le=100)
    result: Optional["ImportResult"] = None
    estimated_time_seconds: Optional[int] = None


class ImportResult(BaseModel):
    """Import parsing result schema."""
    
    team_config: Optional[CreateTeamRequest] = None
    warnings: List[Dict[str, str]] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)


class ConfirmImportRequest(BaseModel):
    """Import confirmation request schema."""
    
    team_name: str
    apply_overrides: Optional[Dict[str, Any]] = None


# ============================================================================
# Skill Management Schemas
# ============================================================================

class SkillInfo(BaseModel):
    """Skill information schema."""
    
    name: str
    description: str
    category: str
    enabled: bool
    path: str


class UpdateAgentSkillsRequest(BaseModel):
    """Agent skills update request schema."""
    
    skills: List[str]


class UpdateAgentSkillsResponse(BaseModel):
    """Agent skills update response schema."""
    
    status: str
    agent: str
    skills: List[str]
    updated_at: datetime


# ============================================================================
# Pagination Schema
# ============================================================================

class PaginationInfo(BaseModel):
    """Pagination metadata schema."""
    
    page: int
    page_size: int
    total: int
    total_pages: int


# Forward reference updates
TeamSummary.model_rebuild()
ExecutionSummary.model_rebuild()
ExecutionDetail.model_rebuild()
ImportTaskStatus.model_rebuild()
