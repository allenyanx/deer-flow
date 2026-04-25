"""DeerTeamX 执行管理 API 路由。

该模块提供触发执行、查询状态以及 WebSocket 实时推送的 RESTful 接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.database.session import get_db
from deerteamx.runtime.executor import TeamExecutor
from deerteamx.runtime.ws_bridge import SSEToWebSocketBridge
from deerteamx.runtime.lock_manager import LockManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


class TriggerExecutionRequest:
    """触发执行的请求体模型（简化版，实际可用 Pydantic）。"""
    def __init__(self, team_id: str, input_data: dict):
        self.team_id = team_id
        self.input_data = input_data


@router.post("")
async def trigger_execution(
    request: dict, 
    db: AsyncSession = Depends(get_db),
    user_id: str = "test-user" # 实际应从 JWT Token 中提取
):
    """触发团队执行。
    
    Request Body:
    {
        "team_id": "team-analytics-dashboard",
        "input_data": {"query": "分析Q1销售数据"}
    }
    """
    team_id = request.get("team_id")
    if not team_id:
        raise HTTPException(status_code=400, detail="team_id is required")
    
    try:
        # 1. 获取团队配置 (此处简化，实际应从 DB 或配置中心加载)
        # team_config = await get_team_config(request["team_id"])
        # 为测试目的使用 Mock 配置
        team_config = {
            "roles": [{"role_id": "r1", "agent_name": "test-agent"}],
            "tasks": [{"task_id": "t1", "dependencies": []}]
        }
        
        # 2. 尝试获取 Read-Only 锁（防止并发执行同一团队）
        lock_manager = LockManager(db)
        execution_id_preview = f"exec-placeholder"  # 预生成占位符，实际 ID 在 execute_team 中生成
        
        # 先检查是否已有锁
        current_owner = await lock_manager.get_execution_lock_owner(team_id)
        if current_owner:
            logger.warning(f"Team {team_id} is currently locked by execution {current_owner}")
            raise HTTPException(
                status_code=423,
                detail="EXECUTION_LOCKED",
                headers={"X-Lock-Owner": current_owner}
            )
        
        # 3. 创建执行记录并获取真实的 execution_id
        executor = TeamExecutor(db)
        execution_id = await executor.execute_team(
            team_id=team_id,
            team_config=team_config,
            input_data=request.get("input_data", {}),
            user_id=user_id
        )
        
        # 4. 获取执行锁（使用真实的 execution_id）
        locked = await lock_manager.acquire_execution_lock(
            team_id=team_id,
            execution_id=execution_id,
            ttl_seconds=1800  # 30分钟超时
        )
        
        if not locked:
            # 如果加锁失败，可能是并发冲突，需要清理已创建的 execution 记录
            logger.error(f"Failed to acquire lock for execution {execution_id}")
            raise HTTPException(
                status_code=423,
                detail="EXECUTION_LOCKED",
                headers={"X-Lock-Owner": "unknown"}
            )
        
        logger.info(f"Execution {execution_id} triggered successfully with lock acquired")
        
        return {
            "execution_id": execution_id,
            "status": "pending",
            "message": "Execution triggered successfully",
            "lock_timeout_seconds": 1800
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}")
async def get_execution_status(execution_id: str, db: AsyncSession = Depends(get_db)):
    """查询执行状态及结果。"""
    executor = TeamExecutor(db)
    execution = await executor.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return execution.to_dict()


@router.post("/{execution_id}/resume")
async def resume_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = "test-user"  # 实际应从 JWT Token 中提取
):
    """从断点恢复执行。
    
    当执行因异常中断时，可以从最后一个成功的 checkpoint 继续执行，
    而不是从头开始。适用于长时间运行的任务或网络不稳定的场景。
    
    Args:
        execution_id: 需要恢复的执行ID
        db: 数据库会话
        user_id: 用户ID（用于权限校验）
        
    Returns:
        {
            "success": true,
            "message": "Execution resumed successfully",
            "resumed_from_task": "task_2",
            "pending_tasks_count": 3
        }
        
    Raises:
        HTTPException: 404 如果执行记录不存在
        HTTPException: 400 如果无法恢复（没有 checkpoint 或已全部完成）
        HTTPException: 423 如果执行正在运行中（锁冲突）
        
    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/executions/exec-20260425-abc123/resume \
          -H "Authorization: Bearer <token>"
        ```
    """
    try:
        # 1. 验证执行记录存在
        executor = TeamExecutor(db)
        execution = await executor.get_execution(execution_id)
        
        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"Execution {execution_id} not found"
            )
        
        # 2. 检查执行状态（只有 failed/cancelled 可以恢复）
        if execution.status in ["running", "completed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume execution with status '{execution.status}'"
            )
        
        # 3. 尝试获取锁（防止并发恢复）
        lock_manager = LockManager(db)
        current_owner = await lock_manager.get_execution_lock_owner(execution.team_id)
        
        if current_owner and current_owner != execution_id:
            logger.warning(f"Team {execution.team_id} is locked by execution {current_owner}")
            raise HTTPException(
                status_code=423,
                detail="EXECUTION_LOCKED",
                headers={"X-Lock-Owner": current_owner}
            )
        
        # 4. 获取团队配置
        # 从 team_versions 表获取最新的配置快照
        from sqlalchemy import select
        from deerteamx.models.base import TeamVersion
        
        stmt = (
            select(TeamVersion)
            .where(TeamVersion.team_id == execution.team_id)
            .order_by(TeamVersion.version_number.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest_version = result.scalar_one_or_none()
        
        if not latest_version:
            # 如果没有版本记录，尝试从 teams 表获取当前配置
            from deerteamx.models.base import Team
            stmt = select(Team).where(Team.team_id == execution.team_id)
            result = await db.execute(stmt)
            team = result.scalar_one_or_none()
            
            if not team:
                raise HTTPException(
                    status_code=404,
                    detail=f"Team {execution.team_id} not found"
                )
            
            team_config = team.config_snapshot
        else:
            team_config = latest_version.config_snapshot
        
        # 5. 获取最后的 checkpoint 信息（用于返回）
        last_checkpoint = await executor._get_last_checkpoint(execution_id)
        
        if not last_checkpoint:
            raise HTTPException(
                status_code=400,
                detail="No checkpoint found. Cannot resume execution from scratch."
            )
        
        # 6. 计算待执行任务数量（用于返回）
        pending_tasks = await executor._get_pending_tasks(
            execution_id=execution_id,
            team_config=team_config,
            last_checkpoint=last_checkpoint
        )
        
        if not pending_tasks:
            # 所有任务已完成，直接标记为 completed
            await executor._update_status(
                execution_id,
                "completed",
                output_data={"resumed_from": last_checkpoint["task_id"], "note": "All tasks already completed"}
            )
            
            return {
                "success": True,
                "message": "All tasks were already completed. Execution marked as completed.",
                "resumed_from_task": last_checkpoint["task_id"],
                "pending_tasks_count": 0,
                "status": "completed"
            }
        
        # 7. 获取执行锁
        locked = await lock_manager.acquire_execution_lock(
            team_id=execution.team_id,
            execution_id=execution_id,
            ttl_seconds=1800  # 30分钟超时
        )
        
        if not locked:
            raise HTTPException(
                status_code=423,
                detail="Failed to acquire lock for resume operation"
            )
        
        logger.info(f"Resuming execution {execution_id} from task {last_checkpoint['task_id']}")
        
        # 8. 异步启动恢复执行
        import asyncio
        asyncio.create_task(
            executor._resume_execution(
                execution_id=execution_id,
                team_config=team_config,
                input_data=execution.input_data or {}
            )
        )
        
        # 9. 更新状态为 running
        await executor._update_status(execution_id, "running")
        
        return {
            "success": True,
            "message": "Execution resumed successfully",
            "resumed_from_task": last_checkpoint["task_id"],
            "pending_tasks_count": len(pending_tasks),
            "status": "running",
            "lock_timeout_seconds": 1800
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume execution {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.websocket("/ws/{execution_id}")
async def websocket_execution_endpoint(
    websocket: WebSocket, 
    execution_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """WebSocket 实时推送执行状态。
    
    前端连接示例: ws://localhost:8000/api/v1/executions/ws/{execution_id}
    """
    # 1. 查询对应的 thread_id
    executor = TeamExecutor(db)
    execution = await executor.get_execution(execution_id)
    
    if not execution:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Execution not found"})
        await websocket.close()
        return

    # 2. 启动桥接器
    bridge = SSEToWebSocketBridge()
    await bridge.bridge(websocket, execution.thread_id, execution_id)
