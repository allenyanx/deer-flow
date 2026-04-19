"""Template Management API Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any, List, Optional

from deerteamx.api.schemas.team_schemas import (
    CreateTemplateRequest,
    UseTemplateRequest,
    TemplateSummary,
    TeamDetail,
)

router = APIRouter(
    prefix="/templates",
    tags=["template-management"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
    },
)


@router.post("", response_model=TemplateSummary, status_code=status.HTTP_201_CREATED)
async def create_template(data: CreateTemplateRequest) -> Any:
    """Save team configuration as a reusable template.
    
    Args:
        data: Team ID, template name, description, and scope
        
    Returns:
        Created template summary
        
    Raises:
        HTTPException: 403 if not team owner (for personal templates)
    """
    # TODO: Implement template creation
    # 1. Verify team exists
    # 2. Check permissions (personal templates require ownership)
    # 3. Snapshot team config
    # 4. Save to templates table
    # 5. Return template summary
    pass


@router.get("", response_model=List[TemplateSummary])
async def list_templates(
    scope: Optional[str] = Query(None, pattern="^(system|personal|all)$"),
    keyword: Optional[str] = Query(None),
) -> Any:
    """List available templates (system + personal).
    
    Args:
        scope: Filter by scope (system/personal/all)
        keyword: Search by template name
        
    Returns:
        List of template summaries sorted by usage_count
    """
    # TODO: Implement template listing
    # 1. Build query based on scope
    # 2. For 'personal' or 'all', filter by current user's templates
    # 3. For 'system', include all system templates
    # 4. Apply keyword search
    # 5. Sort by usage_count descending
    # 6. Return template list
    pass


@router.post("/{template_id}/use", response_model=TeamDetail, status_code=status.HTTP_201_CREATED)
async def use_template(template_id: str, data: UseTemplateRequest) -> Any:
    """Create a new team from a template with optional overrides.
    
    Args:
        template_id: Template identifier
        data: New team name and configuration overrides
        
    Returns:
        Created team details
        
    Raises:
        HTTPException: 404 if template not found
        HTTPException: 403 if trying to use deleted personal template
    """
    # TODO: Implement template usage
    # 1. Query template from database
    # 2. Check template accessibility (system or owned by user)
    # 3. Apply overrides to template config
    # 4. Create new team (reuse create_team logic)
    # 5. Increment template usage_count
    # 6. Return created team
    pass


@router.delete("/{template_id}", status_code=status.HTTP_200_OK)
async def delete_template(template_id: str) -> Any:
    """Soft delete a personal template.
    
    Args:
        template_id: Template identifier
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 403 if not template owner or trying to delete system template
        HTTPException: 404 if template not found
    """
    # TODO: Implement template deletion
    # 1. Query template
    # 2. Verify ownership (cannot delete system templates)
    # 3. Soft delete (set deleted_at)
    # 4. Return success message
    pass
