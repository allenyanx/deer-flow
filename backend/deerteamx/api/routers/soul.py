"""SOUL.md 模板 API

提供 SOUL.md 模板相关的 API 接口：
- 获取可用模板列表
- 预览生成的 SOUL.md 内容
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deerteamx.api.dependencies import get_current_user
from deerteamx.models.base import User
from deerteamx.graph.soul_templates import list_templates, get_template
from deerteamx.services.team_service import TeamService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/soul",
    tags=["SOUL.md Templates"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Pydantic Schemas
# ============================================================================

class SoulTemplateInfo(BaseModel):
    """模板信息"""
    id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板显示名称")
    description: str = Field(..., description="模板描述")
    icon: str = Field(..., description="图标标识")


class SoulTemplateListResponse(BaseModel):
    """模板列表响应"""
    data: Dict[str, Any] = Field(..., description="响应数据")


class SoulPreviewRequest(BaseModel):
    """SOUL.md 预览请求"""
    name: str = Field(..., description="角色名称")
    goal: str = Field(..., description="角色目标")
    backstory: str = Field(..., description="背景故事")
    skills: Optional[list[str]] = Field(default=None, description="技能列表")
    model: Optional[str] = Field(default=None, description="LLM模型")
    soul_template: Optional[str] = Field(default=None, description="指定模板名称")
    allow_delegation: Optional[bool] = Field(default=False, description="是否允许委派")
    tool_groups: Optional[list[str]] = Field(default=None, description="工具组列表")


class SoulPreviewResponse(BaseModel):
    """SOUL.md 预览响应"""
    data: Dict[str, str] = Field(..., description="响应数据，包含 soul_content")


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/templates", response_model=SoulTemplateListResponse)
async def get_soul_templates(
    current_user: User = Depends(get_current_user)
):
    """获取可用模板列表
    
    返回所有可用的 SOUL.md 预设模板类型及其元数据。
    
    **权限**: 已认证用户
    
    **响应示例**:
    ```json
    {
      "data": {
        "templates": [
          {
            "id": "auto",
            "name": "🤖 自动选择（推荐）",
            "description": "系统根据角色特征智能匹配最合适的模板",
            "icon": "robot"
          },
          {
            "id": "default",
            "name": "📋 通用标准",
            "description": "适用于大多数常规角色，平衡简洁性和完整性",
            "icon": "file-text"
          }
        ]
      }
    }
    ```
    """
    # 定义模板元数据（与 soul_templates.py 中的模板对应）
    template_metadata = {
        "auto": {
            "id": "auto",
            "name": "🤖 自动选择（推荐）",
            "description": "系统根据角色特征智能匹配最合适的模板",
            "icon": "robot"
        },
        "default": {
            "id": "default",
            "name": "📋 通用标准",
            "description": "适用于大多数常规角色，平衡简洁性和完整性",
            "icon": "file-text"
        },
        "expert_analyst": {
            "id": "expert_analyst",
            "name": "🔬 专家分析型",
            "description": "数据分析师、研究员等，强调方法论和批判性思维",
            "icon": "microscope"
        },
        "creative_creator": {
            "id": "creative_creator",
            "name": "🎨 创意创作型",
            "description": "文案撰写、内容创作等，鼓励创新和情感共鸣",
            "icon": "palette"
        },
        "technical_developer": {
            "id": "technical_developer",
            "name": "💻 技术开发型",
            "description": "程序员、架构师等，强调代码质量和最佳实践",
            "icon": "code"
        },
        "coordinator_manager": {
            "id": "coordinator_manager",
            "name": "👥 协调管理型",
            "description": "项目经理、团队领导等，强调沟通和资源调配",
            "icon": "users"
        },
        "quality_assurance": {
            "id": "quality_assurance",
            "name": "✅ 质量控制型",
            "description": "测试工程师、审核员等，强调细致和系统性",
            "icon": "check-circle"
        }
    }
    
    # 获取实际可用的模板列表
    available_templates = list_templates()
    
    # 构建响应（按预定义顺序）
    templates_list = []
    templates_list.append(template_metadata["auto"])  # auto 始终在最前
    
    for template_id in available_templates:
        if template_id in template_metadata:
            templates_list.append(template_metadata[template_id])
    
    return SoulTemplateListResponse(
        data={"templates": templates_list}
    )


@router.post("/preview", response_model=SoulPreviewResponse)
async def preview_soul_content(
    request: SoulPreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """预览生成的 SOUL.md 内容
    
    根据角色配置预览生成的 SOUL.md 内容（不保存到数据库）。
    此接口用于前端在用户点击「预览」按钮时实时展示生成结果。
    
    **权限**: 已认证用户
    
    **请求体**:
    ```json
    {
      "name": "Data Analyst",
      "goal": "Analyze Q1 sales data and identify trends",
      "backstory": "You are a senior data scientist...",
      "skills": ["data-analysis", "chart-visualization"],
      "model": "gpt-4-turbo",
      "soul_template": "expert_analyst",
      "allow_delegation": false,
      "tool_groups": ["bash", "file_read"]
    }
    ```
    
    **响应示例**:
    ```json
    {
      "data": {
        "soul_content": "# Expert Analyst: Data Analyst\\n\\n## Professional Background\\n..."
      }
    }
    ```
    
    **注意**: 
    - 此接口仅用于预览，不会保存到数据库
    - 支持自定义模板名称（soul_template），或使用 "auto" 自动选择
    - 如果提供了 soul_content 字段，将直接返回该内容（自定义优先）
    """
    try:
        # 构建角色配置字典
        role_config = {
            "name": request.name,
            "goal": request.goal,
            "backstory": request.backstory,
            "skills": request.skills,
            "model": request.model,
            "soul_template": request.soul_template if request.soul_template != "auto" else None,
            "allow_delegation": request.allow_delegation,
            "tool_groups": request.tool_groups,
        }
        
        # 使用 TeamService 生成 SOUL.md 内容
        soul_content = TeamService.generate_soul_content(
            role=role_config,
            template_name=request.soul_template if request.soul_template != "auto" else None
        )
        
        logger.info(
            f"Generated SOUL.md preview for role '{request.name}' "
            f"({len(soul_content)} chars)"
        )
        
        return SoulPreviewResponse(
            data={"soul_content": soul_content}
        )
    
    except Exception as e:
        logger.error(f"Failed to generate SOUL.md preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SOUL.md preview: {str(e)}"
        )
