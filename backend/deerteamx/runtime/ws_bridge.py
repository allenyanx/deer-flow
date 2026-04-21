"""DeerTeamX 运行时桥接层。

该模块负责将 DeerFlow Gateway 的 SSE 事件流转换为 WebSocket 消息，
并处理 execution_id 与 thread_id 之间的映射关系。
"""

import json
import logging
from typing import Optional

import httpx
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SSEToWebSocketBridge:
    """将 DeerFlow SSE 事件桥接为 WebSocket 消息。"""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        self.gateway_url = gateway_url

    async def bridge(self, websocket: WebSocket, thread_id: str, execution_id: Optional[str] = None):
        """建立桥接并转发事件。
        
        Args:
            websocket: 前端 WebSocket 连接。
            thread_id: DeerFlow 内部的会话标识。
            execution_id: DeerTeamX 业务层的执行标识（可选）。
        """
        await websocket.accept()
        logger.info(f"Bridging SSE to WS for thread: {thread_id}")

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{self.gateway_url}/api/v1/threads/{thread_id}/stream",
                    timeout=None,
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            event_data = line[6:]
                            ws_message = self._format_ws_message(event_data, thread_id, execution_id)
                            await websocket.send_json(ws_message)

                            # 检测执行结束
                            try:
                                payload = json.loads(event_data)
                                if payload.get("event") == "on_chain_end":
                                    break
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Bridge error: {e}")
            await websocket.send_json({"type": "error", "message": str(e)})
        finally:
            await websocket.close()

    def _format_ws_message(self, sse_data: str, thread_id: str, execution_id: Optional[str]) -> dict:
        """格式化 WebSocket 消息。"""
        return {
            "type": "execution_update",
            "execution_id": execution_id,
            "thread_id": thread_id,
            "payload": self._parse_sse_event(sse_data),
        }

    @staticmethod
    def _parse_sse_event(data: str) -> dict:
        """解析 SSE data 字段。"""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"raw": data, "status": "unknown"}
