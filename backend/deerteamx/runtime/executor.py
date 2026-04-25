"""DeerTeamX 团队执行引擎。

该模块负责协调 StaticTeamGraph 的执行，管理 execution_id 生命周期，
并处理与 DeerFlow Gateway 的交互。
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from deerteamx.models.base import Execution
from deerteamx.graph.builder import StaticTeamGraphBuilder

logger = logging.getLogger(__name__)


class TeamExecutor:
    """团队执行引擎核心类。"""

    def __init__(self, db_session: AsyncSession, gateway_url: str = "http://localhost:8001"):
        self.db = db_session
        self.gateway_url = gateway_url

    async def execute_team(self, team_id: str, team_config: dict, input_data: dict, user_id: str) -> str:
        """触发团队执行流程。
        
        Args:
            team_id: 团队配置标识。
            team_config: 解析后的团队配置字典。
            input_data: 用户输入的初始参数。
            user_id: 触发执行的用户标识。
            
        Returns:
            execution_id: 业务层执行标识。
            
        Raises:
            ValueError: 如果配置不完整(缺少roles或tasks)
        """
        # 0. 配置完整性校验
        roles = team_config.get("roles", [])
        tasks = team_config.get("tasks", [])
        
        if not roles:
            raise ValueError("INCOMPLETE_CONFIG: 团队配置缺少角色定义(roles)")
        
        if not tasks:
            raise ValueError("INCOMPLETE_CONFIG: 团队配置缺少任务定义(tasks)")
        
        # 1. 生成唯一标识
        execution_id = f"exec-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        thread_id = f"thread-{uuid.uuid4().hex}"

        # 2. 创建执行记录 (Status: pending)
        execution = Execution(
            execution_id=execution_id,
            team_id=team_id,
            thread_id=thread_id,
            status="pending",
            input_data=input_data,
            created_by=user_id
        )
        self.db.add(execution)
        await self.db.commit()

        # 3. 异步启动后台执行任务
        asyncio.create_task(self._run_execution(execution_id, thread_id, team_config, input_data))

        return execution_id

    async def _run_execution(self, execution_id: str, thread_id: str, team_config: dict, input_data: dict):
        """后台执行逻辑：构建图、运行节点、更新状态。"""
        try:
            # 更新状态为 running
            await self._update_status(execution_id, "running")

            # 构建静态团队图
            builder = StaticTeamGraphBuilder(team_config, self.gateway_url)
            graph = builder.build()

            # 准备 LangGraph 配置（注入 thread_id）
            from langchain_core.runnables import RunnableConfig
            config = RunnableConfig(configurable={"thread_id": thread_id})

            # 执行图
            logger.info(f"Starting execution {execution_id} with thread {thread_id}")
            result = await graph.ainvoke(
                {
                    "messages": [{"role": "user", "content": input_data.get("query", "")}],
                    "input_data": input_data
                },
                config=config
            )

            # 提取统计信息（此处简化，实际应从 Middleware 或 State 中提取 Token 消耗）
            token_stats = self._extract_token_stats(result)

            # 更新状态为 completed
            await self._update_status(
                execution_id, 
                "completed", 
                output_data=result,
                execution_order=result.get("execution_order", []),
                **token_stats
            )

        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}", exc_info=True)
            await self._update_status(execution_id, "failed", error_message=str(e))

    async def _update_status(self, execution_id: str, status: str, **kwargs):
        """原子性更新执行状态及关联数据。"""
        update_data = {"status": status}
        
        if status == "running":
            update_data["started_at"] = datetime.now(timezone.utc)
        elif status in ["completed", "failed", "cancelled"]:
            update_data["completed_at"] = datetime.now(timezone.utc)
            
        update_data.update(kwargs)

        stmt = (
            update(Execution)
            .where(Execution.execution_id == execution_id)
            .values(**update_data)
        )
        
        # 使用独立事务块，确保原子性
        # 使用 nested=True 允许在已有事务中创建子事务
        async with self.db.begin_nested():
            await self.db.execute(stmt)

    @staticmethod
    def _extract_token_stats(result: dict) -> dict:
        """从执行结果中提取 Token 统计信息。"""
        # 简化实现：实际项目中需结合 TokenUsageMiddleware 的记录
        return {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_cents": 0
        }

    async def get_execution(self, execution_id: str) -> Execution:
        """查询执行详情。"""
        stmt = select(Execution).where(Execution.execution_id == execution_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
