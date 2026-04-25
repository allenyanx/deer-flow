"""Team Management Service Layer

提供团队管理的核心业务逻辑，包括：
- 团队CRUD操作
- 版本管理
- Custom Agent同步
- 名称唯一性校验
- 乐观锁控制
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from deerteamx.models.base import Execution, Team, TeamVersion, User
from deerteamx.utils.kms import get_kms
from deerteamx.config.settings import get_settings

logger = logging.getLogger(__name__)


class TeamService:
    """团队管理服务类
    
    负责处理所有团队相关的业务逻辑，确保数据一致性和完整性。
    与DeerFlow Gateway API集成以同步Custom Agent配置。
    """
    
    def __init__(self, db_session: AsyncSession):
        """初始化服务
        
        Args:
            db_session: 异步数据库会话
        """
        self.db = db_session
        self.settings = get_settings()
        self.kms = get_kms(self.settings.ENCRYPTION_MASTER_KEY)
    
    # =========================================================================
    # 团队创建
    # =========================================================================
    
    async def create_team(
        self,
        team_data: Dict[str, Any],
        user_id: UUID
    ) -> Team:
        """创建新团队
        
        业务流程：
        1. 验证团队名称唯一性（同一用户下）
        2. 为每个角色创建/更新DeerFlow Custom Agent
        3. 保存团队配置到数据库
        4. 创建初始版本快照（v0.1.0）
        
        Args:
            team_data: 团队配置数据（包含name/description/execution_mode/roles/tasks/global_settings）
            user_id: 创建者用户ID
            
        Returns:
            创建的Team实例
            
        Raises:
            ValueError: 团队名称已存在
            Exception: Custom Agent创建失败
        """
        # 1. 验证名称唯一性
        await self._validate_team_name_unique(team_data["name"], user_id)
        
        # 2. 生成team_id（基于名称的slug格式）
        team_id = self._generate_team_id(team_data["name"])
        
        # 3. 为每个角色创建Custom Agent
        await self._sync_custom_agents(team_data.get("roles", []))
        
        # 4. 构建config_snapshot（完整配置快照）
        config_snapshot = {
            "name": team_data["name"],
            "description": team_data.get("description"),
            "execution_mode": team_data["execution_mode"],
            "roles": [role.dict() if hasattr(role, 'dict') else role for role in team_data.get("roles", [])],
            "tasks": [task.dict() if hasattr(task, 'dict') else task for task in team_data.get("tasks", [])],
            "global_settings": team_data.get("global_settings", {}).dict() if hasattr(team_data.get("global_settings"), 'dict') else team_data.get("global_settings", {})
        }
        
        # 5. 创建Team记录
        team = Team(
            team_id=team_id,
            name=team_data["name"],
            description=team_data.get("description"),
            execution_mode=team_data["execution_mode"],
            status="draft",
            creator_id=user_id,
            current_version="v0.1.0",
            config_snapshot=config_snapshot
        )
        
        self.db.add(team)
        await self.db.flush()  # 获取team_id
        
        # 6. 创建初始版本快照
        await self._create_version_snapshot(
            team_id=team_id,
            version_number=1,
            version_tag="v0.1.0",
            config_snapshot=config_snapshot,
            change_summary="初始版本",
            created_by=user_id
        )
        
        await self.db.commit()
        await self.db.refresh(team)
        
        logger.info(f"✅ 团队创建成功: team_id={team_id}, name={team.name}")
        return team
    
    # =========================================================================
    # 团队查询
    # =========================================================================
    
    async def get_team_by_id(self, team_id: str, user_id: UUID) -> Team:
        """根据ID获取团队详情
        
        Args:
            team_id: 团队ID
            user_id: 当前用户ID（用于权限校验）
            
        Returns:
            Team实例
            
        Raises:
            ValueError: 团队不存在或无权限访问
        """
        stmt = (
            select(Team)
            .where(
                and_(
                    Team.team_id == team_id,
                    Team.deleted_at.is_(None)  # 排除已删除的团队
                )
            )
            .options(selectinload(Team.creator))
        )
        
        result = await self.db.execute(stmt)
        team = result.scalar_one_or_none()
        
        if not team:
            raise ValueError(f"团队不存在: {team_id}")
        
        # 权限校验：仅允许创建者查看
        if team.creator_id != user_id:
            raise ValueError("无权访问此团队")
        
        return team
    
    async def list_teams(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_by: str = "update_time",
        sort_order: str = "desc"
    ) -> Tuple[List[Team], int]:
        """分页查询团队列表
        
        Args:
            user_id: 当前用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            status: 状态筛选（draft/executing/completed/failed）
            keyword: 关键词搜索（团队名称模糊匹配）
            sort_by: 排序字段（create_time/update_time/name）
            sort_order: 排序方向（asc/desc）
            
        Returns:
            (团队列表, 总数)
        """
        # 构建基础查询
        stmt = (
            select(Team)
            .where(
                and_(
                    Team.creator_id == user_id,
                    Team.deleted_at.is_(None)
                )
            )
            .options(selectinload(Team.creator))
        )
        
        # 应用状态筛选
        if status:
            stmt = stmt.where(Team.status == status)
        
        # 应用关键词搜索
        if keyword:
            stmt = stmt.where(Team.name.ilike(f"%{keyword}%"))
        
        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()
        
        # 应用排序
        sort_field_map = {
            "create_time": Team.created_at,
            "update_time": Team.updated_at,
            "name": Team.name
        }
        sort_field = sort_field_map.get(sort_by, Team.updated_at)
        
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_field.asc())
        else:
            stmt = stmt.order_by(sort_field.desc())
        
        # 应用分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        result = await self.db.execute(stmt)
        teams = result.scalars().all()
        
        return list(teams), total
    
    # =========================================================================
    # 团队更新
    # =========================================================================
    
    async def update_team(
        self,
        team_id: str,
        update_data: Dict[str, Any],
        user_id: UUID,
        expected_version: Optional[str] = None
    ) -> Team:
        """更新团队配置（支持乐观锁）
        
        业务流程：
        1. 检查团队是否正在执行中（Read-Only锁）
        2. 验证资源所有权
        3. 乐观锁校验（版本号匹配）
        4. 如果角色变更，同步更新Custom Agents
        5. 保存新版本快照
        6. 递增版本号
        
        Args:
            team_id: 团队ID
            update_data: 更新数据（部分更新）
            user_id: 当前用户ID
            expected_version: 期望的版本号（乐观锁）
            
        Returns:
            更新后的Team实例
            
        Raises:
            ValueError: 团队正在执行中/无权限/版本冲突
        """
        # 1. 获取现有团队
        team = await self.get_team_by_id(team_id, user_id)
        
        # 2. 检查Read-Only锁（团队不能在执行中）
        if team.status == "executing":
            raise ValueError("团队正在执行中，无法更新")
        
        # 3. 乐观锁校验
        if expected_version and team.current_version != expected_version:
            raise ValueError(
                f"版本冲突：当前版本 {team.current_version}，期望版本 {expected_version}"
            )
        
        # 4. 提取更新字段
        config_snapshot = team.config_snapshot.copy()
        
        if "name" in update_data and update_data["name"]:
            # 验证新名称唯一性
            await self._validate_team_name_unique(update_data["name"], user_id, exclude_team_id=team_id)
            team.name = update_data["name"]
            config_snapshot["name"] = update_data["name"]
        
        if "description" in update_data:
            team.description = update_data["description"]
            config_snapshot["description"] = update_data["description"]
        
        if "execution_mode" in update_data and update_data["execution_mode"]:
            team.execution_mode = update_data["execution_mode"]
            config_snapshot["execution_mode"] = update_data["execution_mode"]
        
        # 5. 如果角色变更，同步Custom Agents
        if "roles" in update_data and update_data["roles"]:
            roles_data = [
                role.dict() if hasattr(role, 'dict') else role 
                for role in update_data["roles"]
            ]
            await self._sync_custom_agents(roles_data)
            config_snapshot["roles"] = roles_data
        
        if "tasks" in update_data and update_data["tasks"]:
            tasks_data = [
                task.dict() if hasattr(task, 'dict') else task 
                for task in update_data["tasks"]
            ]
            config_snapshot["tasks"] = tasks_data
        
        if "global_settings" in update_data and update_data["global_settings"]:
            settings_data = (
                update_data["global_settings"].dict() 
                if hasattr(update_data["global_settings"], 'dict') 
                else update_data["global_settings"]
            )
            config_snapshot["global_settings"] = settings_data
        
        # 6. 更新config_snapshot和版本号
        team.config_snapshot = config_snapshot
        new_version = self._increment_version(team.current_version)
        team.current_version = new_version
        
        await self.db.flush()
        
        # 7. 创建新版本快照
        version_number = await self._get_next_version_number(team_id)
        await self._create_version_snapshot(
            team_id=team_id,
            version_number=version_number,
            version_tag=new_version,
            config_snapshot=config_snapshot,
            change_summary=self._generate_change_summary(update_data),
            created_by=user_id
        )
        
        await self.db.commit()
        await self.db.refresh(team)
        
        logger.info(f"✅ 团队更新成功: team_id={team_id}, version={new_version}")
        return team
    
    # =========================================================================
    # 团队删除
    # =========================================================================
    
    async def delete_team(self, team_id: str, user_id: UUID) -> None:
        """软删除团队（标记deleted_at）
        
        Args:
            team_id: 团队ID
            user_id: 当前用户ID
            
        Raises:
            ValueError: 团队正在执行中/无权限
        """
        # 1. 获取团队
        team = await self.get_team_by_id(team_id, user_id)
        
        # 2. 检查是否正在执行
        if team.status == "executing":
            raise ValueError("团队正在执行中，无法删除")
        
        # 3. 软删除
        team.deleted_at = datetime.now(timezone.utc)
        team.status = "failed"  # 标记为失败状态
        
        await self.db.commit()
        
        logger.info(f"✅ 团队删除成功: team_id={team_id}")
    
    # =========================================================================
    # 名称唯一性校验
    # =========================================================================
    
    async def check_name_availability(
        self,
        name: str,
        user_id: UUID,
        exclude_team_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """检查团队名称可用性
        
        Args:
            name: 待检查的团队名称
            user_id: 当前用户ID
            exclude_team_id: 排除的团队ID（用于更新场景）
            
        Returns:
            (是否可用, 建议名称)
        """
        stmt = (
            select(Team)
            .where(
                and_(
                    Team.name == name,
                    Team.creator_id == user_id,
                    Team.deleted_at.is_(None)
                )
            )
        )
        
        if exclude_team_id:
            stmt = stmt.where(Team.team_id != exclude_team_id)
        
        result = await self.db.execute(stmt)
        existing_team = result.scalar_one_or_none()
        
        if not existing_team:
            return True, None
        
        # 生成建议名称
        suggested_name = self._generate_suggested_name(name, user_id)
        return False, suggested_name
    
    # =========================================================================
    # 私有辅助方法
    # =========================================================================
    
    async def _validate_team_name_unique(
        self,
        name: str,
        user_id: UUID,
        exclude_team_id: Optional[str] = None
    ) -> None:
        """验证团队名称唯一性
        
        Raises:
            ValueError: 名称已存在
        """
        available, _ = await self.check_name_availability(name, user_id, exclude_team_id)
        if not available:
            raise ValueError(f"团队名称 '{name}' 已存在")
    
    async def _sync_custom_agents(self, roles: List[Dict[str, Any]]) -> None:
        """同步Custom Agents到DeerFlow
        
        为每个角色创建或更新DeerFlow Custom Agent配置。
        
        Args:
            roles: 角色配置列表
        """
        # TODO: 调用DeerFlow Gateway API创建Custom Agents
        # 当前阶段先记录日志，后续Phase 2实现
        for role in roles:
            agent_name = role.get("agent_name", role.get("role_id"))
            
            # 规范化 agent_name（确保小写 + 连字符格式）
            normalized_agent_name = self._normalize_agent_name(agent_name)
            if normalized_agent_name != agent_name:
                logger.warning(
                    f"⚠️ Agent name normalized: '{agent_name}' -> '{normalized_agent_name}'"
                )
                role["agent_name"] = normalized_agent_name
            
            logger.info(f"📝 准备创建Custom Agent: {normalized_agent_name}")
            # 实际实现时调用:
            # await deerflow_client.create_agent(agent_config)
    
    def _generate_team_id(self, name: str) -> str:
        """生成团队ID（slug格式）
        
        Args:
            name: 团队名称
            
        Returns:
            slug格式的团队ID（如: team-code-review-001）
        """
        import re
        from uuid import uuid4
        
        # 转换为小写，替换非字母数字字符为连字符
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        
        # 添加UUID前8位确保唯一性
        unique_suffix = str(uuid4())[:8]
        
        return f"team-{slug}-{unique_suffix}"
    
    @staticmethod
    def _normalize_agent_name(agent_name: str) -> str:
        """规范化 Agent 名称为小写 + 连字符格式
        
        将任意格式的 agent_name 转换为 DeerFlow Gateway API 要求的格式：
        - 全部转换为小写
        - 空格和下划线转换为连字符
        - 移除特殊字符（只保留字母、数字、连字符）
        
        Args:
            agent_name: 原始 agent 名称
            
        Returns:
            规范化后的 agent 名称（如: 'code-scanner-v1'）
            
        Examples:
            >>> TeamService._normalize_agent_name("CodeScanner_V1")
            'codescanner-v1'
            >>> TeamService._normalize_agent_name("Data Analyst")
            'data-analyst'
            >>> TeamService._normalize_agent_name("code_reviewer")
            'code-reviewer'
        """
        import re
        
        # 转换为小写
        normalized = agent_name.lower()
        
        # 将空格和下划线转换为连字符
        normalized = re.sub(r'[\s_]+', '-', normalized)
        
        # 移除所有非字母数字和非连字符的字符
        normalized = re.sub(r'[^a-z0-9-]', '', normalized)
        
        # 合并多个连续连字符为单个
        normalized = re.sub(r'-+', '-', normalized)
        
        # 移除首尾的连字符
        normalized = normalized.strip('-')
        
        return normalized
    
    def _increment_version(self, version: str) -> str:
        """递增语义化版本号
        
        Args:
            version: 当前版本（如: v0.1.0）
            
        Returns:
            新版本号（递增patch版本）
        """
        # 移除'v'前缀
        version_str = version.lstrip('v')
        parts = version_str.split('.')
        
        if len(parts) == 3:
            major, minor, patch = map(int, parts)
            patch += 1
            return f"v{major}.{minor}.{patch}"
        
        # 如果格式不正确，返回默认版本
        return "v0.1.0"
    
    async def _get_next_version_number(self, team_id: str) -> int:
        """获取下一个版本号
        
        Args:
            team_id: 团队ID
            
        Returns:
            下一个版本号（最大版本号+1）
        """
        stmt = (
            select(func.max(TeamVersion.version_number))
            .where(TeamVersion.team_id == team_id)
        )
        
        result = await self.db.execute(stmt)
        max_version = result.scalar()
        
        return (max_version or 0) + 1
    
    async def _create_version_snapshot(
        self,
        team_id: str,
        version_number: int,
        version_tag: str,
        config_snapshot: Dict[str, Any],
        change_summary: str,
        created_by: UUID
    ) -> TeamVersion:
        """创建版本快照
        
        Args:
            team_id: 团队ID
            version_number: 版本号（整数）
            version_tag: 版本标签（如: v0.1.0）
            config_snapshot: 配置快照
            change_summary: 变更说明
            created_by: 创建者ID
            
        Returns:
            创建的TeamVersion实例
        """
        version = TeamVersion(
            team_id=team_id,
            version_number=version_number,
            version_tag=version_tag,
            config_snapshot=config_snapshot,
            change_summary=change_summary,
            created_by=created_by
        )
        
        self.db.add(version)
        await self.db.flush()
        
        return version
    
    def _generate_change_summary(self, update_data: Dict[str, Any]) -> str:
        """生成变更说明
        
        Args:
            update_data: 更新数据
            
        Returns:
            变更说明文本
        """
        changes = []
        
        if "name" in update_data:
            changes.append("修改名称")
        if "description" in update_data:
            changes.append("修改描述")
        if "roles" in update_data:
            changes.append("修改角色配置")
        if "tasks" in update_data:
            changes.append("修改任务配置")
        if "global_settings" in update_data:
            changes.append("修改全局设置")
        
        return "；".join(changes) if changes else "配置更新"
    
    def _generate_suggested_name(self, base_name: str, user_id: UUID) -> str:
        """生成建议的团队名称
        
        Args:
            base_name: 基础名称
            user_id: 用户ID
            
        Returns:
            建议名称（如: 代码审查团队(2)）
        """
        # 查询该用户下所有同名团队的序号
        stmt = (
            select(Team.name)
            .where(
                and_(
                    Team.creator_id == user_id,
                    Team.name.like(f"{base_name}(%)"),
                    Team.deleted_at.is_(None)
                )
            )
        )
        
        import re
        result = self.db.execute(stmt)
        existing_names = result.scalars().all()
        
        # 提取已有序号
        existing_numbers = []
        for name in existing_names:
            match = re.search(r'\((\d+)\)$', name)
            if match:
                existing_numbers.append(int(match.group(1)))
        
        # 找到最小的可用序号
        next_number = 1
        while next_number in existing_numbers:
            next_number += 1
        
        return f"{base_name}({next_number})"
    
    # =========================================================================
    # SOUL.md 模板系统
    # =========================================================================
    
    @staticmethod
    def generate_soul_content(
        role: Dict[str, Any],
        template_name: Optional[str] = None
    ) -> str:
        """根据角色配置生成高质量的 SOUL.md 内容
        
        生成策略：
        1. 如果用户提供了 soul_content，直接使用（自定义优先）
        2. 如果指定了 template_name，使用对应模板
        3. 否则根据角色特征自动选择最合适的模板
        
        Args:
            role: 角色配置字典，包含 name/goal/backstory/skills 等字段
            template_name: 可选，指定使用的模板名称
            
        Returns:
            生成的 SOUL.md 内容（Markdown 格式字符串）
            
        Examples:
            >>> role = {
            ...     "name": "Data Analyst",
            ...     "goal": "Analyze sales data and provide insights",
            ...     "backstory": "You are a senior data scientist...",
            ...     "skills": ["data-analysis", "chart-visualization"]
            ... }
            >>> soul = TeamService.generate_soul_content(role)
            >>> print(soul[:100])
            '# Expert Analyst: Data Analyst\n\n## Professional Background\nYou are a senior data scientist...'
        """
        from deerteamx.graph.soul_templates import get_template
        from deerteamx.graph.soul_auto_selector import auto_select_template
        
        # ========== 策略 1：用户自定义内容优先 ==========
        if role.get("soul_content"):
            logger.debug(f"Using custom soul_content for role '{role.get('name')}'")
            return role["soul_content"]
        
        # ========== 策略 2：确定使用的模板 ==========
        if template_name:
            # 用户显式指定模板
            selected_template = template_name
        else:
            # 自动选择模板（基于角色特征启发式判断）
            selected_template = auto_select_template(role)
        
        logger.debug(
            f"Generating soul_content for role '{role.get('name')}' "
            f"using template '{selected_template}'"
        )
        
        # ========== 策略 3：渲染模板 ==========
        try:
            template = get_template(selected_template)
        except ValueError as e:
            logger.warning(f"{e}. Falling back to 'default' template.")
            template = get_template("default")
            selected_template = "default"
        
        # 准备模板变量
        template_vars = {
            "name": role.get("name", "Unknown Role"),
            "goal": role.get("goal", "Complete assigned tasks effectively."),
            "backstory": role.get("backstory", "You are a professional assistant."),
        }
        
        # 渲染模板
        soul_content = template.format(**template_vars)
        
        # ========== 策略 4：追加额外信息（Skills、Delegation 等）==========
        additional_sections = []
        
        # 添加技能信息
        if role.get("skills"):
            skills_list = "\n".join([f"- `{skill}`" for skill in role["skills"]])
            additional_sections.append(f"""
## Available Skills
You have access to the following specialized skills:

{skills_list}

Use these skills when they can help you accomplish your goals more effectively.
""")
        
        # 添加工具组信息
        if role.get("tool_groups"):
            tools_list = "\n".join([f"- `{tool}`" for tool in role["tool_groups"]])
            additional_sections.append(f"""
## Available Tools
You can use the following tool groups:

{tools_list}

Choose the appropriate tools based on the task requirements.
""")
        
        # 添加委派能力说明
        if role.get("allow_delegation"):
            additional_sections.append("""
## Delegation Authority
You have the authority to delegate subtasks to other team members when:
- The task requires specialized expertise you don't possess
- Delegating would improve overall team efficiency
- The subtask is well-defined and can be executed independently

When delegating, clearly specify:
1. The specific task to be completed
2. Expected output format and quality standards
3. Deadline or priority level
""")
        
        # 添加模型配置提示（仅当设置了特定模型时）
        if role.get("model"):
            additional_sections.append(f"""
## Technical Configuration
- **LLM Model**: `{role['model']}`
- Optimize your approach based on this model's strengths and limitations
""")
        
        # 合并所有内容
        if additional_sections:
            soul_content += "\n" + "\n".join(additional_sections)
        
        logger.info(
            f"✅ Generated soul_content for '{role.get('name')}' "
            f"({len(soul_content)} chars, template='{selected_template}')"
        )
        
        return soul_content
