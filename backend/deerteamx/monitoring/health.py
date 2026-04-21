"""DeerTeamX 健康检查与非功能优化探针。

该模块提供深度健康检查接口，用于监控系统各组件（DB, DeerFlow Gateway）的连通性。
"""

import time
import logging
from typing import Dict, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

logger = logging.getLogger(__name__)


class HealthProbe:
    """系统健康探针。"""

    def __init__(self, db_session: AsyncSession, gateway_url: str):
        self.db = db_session
        self.gateway_url = gateway_url

    async def check_all(self) -> Dict[str, Any]:
        """执行全量健康检查。"""
        start_time = time.time()
        
        status = {
            "status": "healthy",
            "version": "1.0.0",
            "checks": {}
        }

        # 1. 数据库检查
        db_status = await self._check_database()
        status["checks"]["database"] = db_status

        # 2. DeerFlow Gateway 检查
        gateway_status = await self._check_deerflow_gateway()
        status["checks"]["deerflow_gateway"] = gateway_status

        # 3. 综合状态判定
        if not db_status["healthy"] or not gateway_status["healthy"]:
            status["status"] = "degraded"
            
        status["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        return status

    async def _check_database(self) -> Dict[str, Any]:
        """检查 PostgreSQL 连通性。"""
        try:
            await self.db.execute(text("SELECT 1"))
            return {"healthy": True, "message": "PostgreSQL connection OK"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"healthy": False, "message": str(e)}

    async def _check_deerflow_gateway(self) -> Dict[str, Any]:
        """检查 DeerFlow Gateway API 可用性。"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.gateway_url}/health")
                if resp.status_code == 200:
                    return {"healthy": True, "message": "Gateway is responsive"}
        except Exception as e:
            logger.error(f"Gateway health check failed: {e}")
        return {"healthy": False, "message": "Gateway unreachable"}
