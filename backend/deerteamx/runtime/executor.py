"""DeerTeamX 团队执行引擎。

该模块负责协调 StaticTeamGraph 的执行，管理 execution_id 生命周期，
并处理与 DeerFlow Gateway 的交互。
支持断点续传功能（Breakpoint Resume）。
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert

from deerteamx.models.base import Execution, ExecutionState
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
        # 从 execution 记录中获取 team_id（用于释放锁）
        from deerteamx.models.base import Execution as ExecutionModel
        from deerteamx.runtime.lock_manager import LockManager
        
        stmt = select(ExecutionModel).where(ExecutionModel.execution_id == execution_id)
        result = await self.db.execute(stmt)
        execution_record = result.scalar_one_or_none()
        
        if not execution_record:
            logger.error(f"Execution record {execution_id} not found")
            return
        
        team_id = execution_record.team_id
        lock_manager = LockManager(self.db)
        
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

            # 序列化输出数据（将 LangChain 消息对象转换为字典）
            serialized_result = self._serialize_execution_result(result)

            # 更新状态为 completed
            await self._update_status(
                execution_id, 
                "completed", 
                output_data=serialized_result,
                execution_order=serialized_result.get("execution_order", []),
                **token_stats
            )

        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}", exc_info=True)
            await self._update_status(execution_id, "failed", error_message=str(e))
        
        finally:
            # 无论成功或失败，都释放锁
            try:
                released = await lock_manager.release_execution_lock(team_id, execution_id)
                if released:
                    logger.info(f"Lock released for execution {execution_id} on team {team_id}")
                else:
                    logger.warning(f"Failed to release lock for execution {execution_id} (may have expired)")
            except Exception as e:
                logger.error(f"Error releasing lock for execution {execution_id}: {e}", exc_info=True)

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
        
        # 直接执行更新，由外层事务管理（避免嵌套事务导致的问题）
        await self.db.execute(stmt)
        await self.db.commit()

    @staticmethod
    def _serialize_message(msg) -> dict:
        """将 LangChain 消息对象序列化为字典。
        
        Args:
            msg: HumanMessage/AIMessage/ToolMessage/SystemMessage 对象
            
        Returns:
            可 JSON 序列化的字典
        """
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
        
        if isinstance(msg, HumanMessage):
            return {
                "type": "human",
                "content": msg.content,
                "id": getattr(msg, "id", None),
            }
        elif isinstance(msg, AIMessage):
            result = {
                "type": "ai",
                "content": msg.content,
                "id": getattr(msg, "id", None),
            }
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                result["tool_calls"] = [
                    {
                        "name": tc.get("name"),
                        "args": tc.get("args"),
                        "id": tc.get("id"),
                    }
                    for tc in msg.tool_calls
                ]
            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                result["usage_metadata"] = msg.usage_metadata
            return result
        elif isinstance(msg, ToolMessage):
            return {
                "type": "tool",
                "content": msg.content,
                "name": getattr(msg, "name", None),
                "tool_call_id": getattr(msg, "tool_call_id", None),
                "id": getattr(msg, "id", None),
            }
        elif isinstance(msg, SystemMessage):
            return {
                "type": "system",
                "content": msg.content,
                "id": getattr(msg, "id", None),
            }
        else:
            # 未知类型，转为字符串
            return {
                "type": "unknown",
                "content": str(msg),
            }

    @staticmethod
    def _serialize_execution_result(result: dict) -> dict:
        """序列化执行结果，确保所有字段都可 JSON 序列化。
        
        Args:
            result: LangGraph 执行结果
            
        Returns:
            可 JSON 序列化的字典
        """
        if not result:
            return {}
        
        serialized = {}
        
        for key, value in result.items():
            if key == "messages" and isinstance(value, list):
                # 序列化消息列表
                serialized[key] = [
                    TeamExecutor._serialize_message(msg) if hasattr(msg, "content") else msg
                    for msg in value
                ]
            elif key == "task_outputs" and isinstance(value, dict):
                # 递归序列化 task_outputs
                serialized_task_outputs = {}
                for task_id, task_result in value.items():
                    if isinstance(task_result, dict):
                        serialized_task_outputs[task_id] = TeamExecutor._serialize_execution_result(task_result)
                    else:
                        serialized_task_outputs[task_id] = task_result
                serialized[key] = serialized_task_outputs
            else:
                # 其他字段直接复制
                serialized[key] = value
        
        return serialized

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

    async def _save_execution_state(
        self,
        execution_id: str,
        task_id: str,
        role_id: str,
        status: str,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> int:
        """保存任务执行状态（checkpoint）。
        
        Args:
            execution_id: 执行ID
            task_id: 任务ID
            role_id: 角色ID
            status: 任务状态 (pending/running/completed/failed)
            input_data: 任务输入数据
            output_data: 任务输出数据
            error_message: 错误信息
            
        Returns:
            state_id: 状态记录ID
        """
        now = datetime.now(timezone.utc)
        
        # 检查是否已存在该任务的状态记录
        stmt = select(ExecutionState).where(
            ExecutionState.execution_id == execution_id,
            ExecutionState.task_id == task_id
        )
        result = await self.db.execute(stmt)
        existing_state = result.scalar_one_or_none()
        
        if existing_state:
            # 更新现有记录
            update_data = {
                "status": status,
                "updated_at": now
            }
            
            if status == "running":
                update_data["started_at"] = now
            elif status in ["completed", "failed"]:
                update_data["completed_at"] = now
                if output_data is not None:
                    update_data["output_data"] = output_data
                if error_message is not None:
                    update_data["error_message"] = error_message
            
            stmt = (
                update(ExecutionState)
                .where(ExecutionState.state_id == existing_state.state_id)
                .values(**update_data)
            )
            await self.db.execute(stmt)
            state_id = existing_state.state_id
        else:
            # 创建新记录
            state_data = {
                "execution_id": execution_id,
                "task_id": task_id,
                "role_id": role_id,
                "status": status,
                "input_data": input_data,
                "created_at": now,
                "updated_at": now
            }
            
            if status == "running":
                state_data["started_at"] = now
            
            stmt = insert(ExecutionState).values(**state_data).returning(ExecutionState.state_id)
            result = await self.db.execute(stmt)
            state_id = result.scalar()
        
        await self.db.commit()
        logger.debug(f"Saved execution state: task={task_id}, status={status}, state_id={state_id}")
        return state_id

    async def _get_last_checkpoint(self, execution_id: str) -> Optional[Dict]:
        """获取最后一个成功的 checkpoint。
        
        Args:
            execution_id: 执行ID
            
        Returns:
            包含最后完成任务信息的字典，如果没有则返回 None
        """
        # 查询所有已完成的任务，按完成时间降序
        stmt = (
            select(ExecutionState)
            .where(
                ExecutionState.execution_id == execution_id,
                ExecutionState.status == "completed"
            )
            .order_by(ExecutionState.completed_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        last_completed = result.scalar_one_or_none()
        
        if not last_completed:
            return None
        
        return {
            "task_id": last_completed.task_id,
            "role_id": last_completed.role_id,
            "output_data": last_completed.output_data,
            "completed_at": last_completed.completed_at
        }

    async def _get_pending_tasks(
        self,
        execution_id: str,
        team_config: dict,
        last_checkpoint: Optional[Dict] = None
    ) -> List[Dict]:
        """获取待执行的任务列表。
        
        Args:
            execution_id: 执行ID
            team_config: 团队配置
            last_checkpoint: 最后的 checkpoint 信息
            
        Returns:
            待执行任务列表
        """
        tasks = team_config.get("tasks", [])
        
        if not last_checkpoint:
            # 没有 checkpoint，返回所有任务
            return tasks
        
        # 找到最后完成任务的索引
        last_task_id = last_checkpoint["task_id"]
        last_task_index = None
        
        for i, task in enumerate(tasks):
            if task.get("task_id") == last_task_id:
                last_task_index = i
                break
        
        if last_task_index is None or last_task_index >= len(tasks) - 1:
            # 未找到或已是最后一个任务
            return []
        
        # 返回后续未完成的任务
        pending_tasks = tasks[last_task_index + 1:]
        logger.info(f"Found {len(pending_tasks)} pending tasks after checkpoint")
        return pending_tasks

    async def _resume_execution(self, execution_id: str, team_config: dict, input_data: dict) -> bool:
        """从断点恢复执行。
        
        Args:
            execution_id: 执行ID
            team_config: 团队配置
            input_data: 原始输入数据
            
        Returns:
            是否成功恢复执行
        """
        logger.info(f"Attempting to resume execution {execution_id}")
        
        # 1. 获取最后的 checkpoint
        last_checkpoint = await self._get_last_checkpoint(execution_id)
        
        if not last_checkpoint:
            logger.warning(f"No checkpoint found for execution {execution_id}, cannot resume")
            return False
        
        logger.info(f"Resuming from checkpoint: task={last_checkpoint['task_id']}")
        
        # 2. 获取待执行任务
        pending_tasks = await self._get_pending_tasks(execution_id, team_config, last_checkpoint)
        
        if not pending_tasks:
            logger.info(f"No pending tasks, execution {execution_id} is complete")
            # 更新执行状态为 completed
            await self._update_status(
                execution_id,
                "completed",
                output_data={"resumed_from": last_checkpoint["task_id"]}
            )
            return True
        
        # 3. 更新执行状态为 running
        await self._update_status(execution_id, "running")
        
        # 4. 构建图并执行剩余任务
        try:
            builder = StaticTeamGraphBuilder(team_config, self.gateway_url)
            graph = builder.build()
            
            # 准备 LangGraph 配置
            from langchain_core.runnables import RunnableConfig
            
            # 获取 thread_id
            stmt = select(Execution).where(Execution.execution_id == execution_id)
            result = await self.db.execute(stmt)
            execution_record = result.scalar_one_or_none()
            
            if not execution_record:
                logger.error(f"Execution record {execution_id} not found")
                return False
            
            thread_id = execution_record.thread_id
            config = RunnableConfig(configurable={"thread_id": thread_id})
            
            # 构造恢复执行的输入（包含 checkpoint 的输出作为上下文）
            resume_input = {
                "messages": [{"role": "user", "content": input_data.get("query", "")}],
                "input_data": input_data,
                "checkpoint": last_checkpoint  # 传递 checkpoint 信息
            }
            
            logger.info(f"Executing {len(pending_tasks)} pending tasks from checkpoint")
            
            # 执行图
            result = await graph.ainvoke(resume_input, config=config)
            
            # 提取统计信息
            token_stats = self._extract_token_stats(result)
            
            # 更新状态为 completed
            await self._update_status(
                execution_id,
                "completed",
                output_data=result,
                execution_order=result.get("execution_order", []),
                **token_stats
            )
            
            logger.info(f"Execution {execution_id} resumed and completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume execution {execution_id}: {e}", exc_info=True)
            await self._update_status(execution_id, "failed", error_message=str(e))
            return False
