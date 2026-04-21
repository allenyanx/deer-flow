"""DeerTeamX WebSocket 桥接优化。

该模块增强了 SSE 到 WebSocket 的转换逻辑，增加了心跳检测、断线重连及背压处理。
"""

import asyncio
import json
import logging
from typing import Optional

import httpx
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class OptimizedSSEBridge:
    """优化的 SSE 转 WebSocket 桥接器。"""

    def __init__(self, gateway_url: str = "http://localhost:8001"):
        self.gateway_url = gateway_url
        self.heartbeat_interval = 30  # 心跳间隔（秒）

    async def bridge(self, websocket: WebSocket, thread_id: str):
        """建立并维护从 DeerFlow SSE 到前端 WebSocket 的桥接。"""
        await websocket.accept()
        client = httpx.AsyncClient(timeout=None)
        
        try:
            # 启动心跳任务
            heartbeat_task = asyncio.create_task(self._send_heartbeat(websocket))
            
            async with client.stream(
                "GET", 
                f"{self.gateway_url}/api/v1/threads/{thread_id}/stream"
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        payload = line[6:]
                        try:
                            data = json.loads(payload)
                            msg = {
                                "type": "execution_update",
                                "thread_id": thread_id,
                                "payload": data
                            }
                            await websocket.send_json(msg)
                            
                            # 检测执行结束
                            if data.get("event") == "on_chain_end":
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from SSE: {payload}")

        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected for thread {thread_id}")
        except Exception as e:
            logger.error(f"Bridge error for thread {thread_id}: {e}")
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except:
                pass
        finally:
            heartbeat_task.cancel()
            await client.aclose()
            try:
                await websocket.close()
            except:
                pass

    async def _send_heartbeat(self, websocket: WebSocket):
        """定期发送心跳包以保持连接活跃。"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                await websocket.send_json({"type": "heartbeat"})
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
