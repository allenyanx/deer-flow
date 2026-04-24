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
    try:
        # 1. 获取团队配置 (此处简化，实际应从 DB 或配置中心加载)
        # team_config = await get_team_config(request["team_id"])
        # 为测试目的使用 Mock 配置
        team_config = {
            "roles": [{"role_id": "r1", "agent_name": "test-agent"}],
            "tasks": [{"task_id": "t1", "dependencies": []}]
        }
        
        executor = TeamExecutor(db)
        execution_id = await executor.execute_team(
            team_id=request["team_id"],
            team_config=team_config,
            input_data=request.get("input_data", {}),
            user_id=user_id
        )
        
        return {
            "execution_id": execution_id,
            "status": "pending",
            "message": "Execution triggered successfully"
        }
    except Exception as e:
        logger.error(f"Failed to trigger execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}")
async def get_execution_status(execution_id: str, db: AsyncSession = Depends(get_db)):
    """查询执行状态及结果。"""
    executor = TeamExecutor(db)
    execution = await executor.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return execution.to_dict()


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
