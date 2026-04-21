"""DeerTeamX 执行记录数据模型。

该模块定义了团队执行实例在 PostgreSQL 中的存储结构，
负责维护 execution_id 与 DeerFlow thread_id 之间的映射关系。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ARRAY
from sqlalchemy.sql import func

from deerteamx.database import Base


class Execution(Base):
    """团队执行实例模型。"""
    
    __tablename__ = "executions"

    # 主键：DeerTeamX 业务层执行ID (格式: exec-YYYYMMDD-xxxx)
    execution_id = Column(String(64), primary_key=True, index=True)
    
    # 外键：关联的团队配置
    team_id = Column(String(64), nullable=False, index=True)
    
    # 外键：关联的 DeerFlow thread_id (用于底层会话追踪)
    thread_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # 执行状态: pending, running, completed, failed, cancelled
    status = Column(String(20), nullable=False, default="pending")
    
    # 执行元数据
    input_data = Column(JSON, nullable=True)  # 用户输入参数
    output_data = Column(JSON, nullable=True)  # 执行结果
    execution_order = Column(ARRAY(String), nullable=True)  # 实际执行顺序
    
    # Token 统计
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_cost_cents = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 审计字段
    created_by = Column(String(64), nullable=False)
    error_message = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        """将模型转换为字典以便 API 响应。"""
        return {
            "execution_id": self.execution_id,
            "team_id": self.team_id,
            "thread_id": self.thread_id,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "execution_order": self.execution_order,
            "token_stats": {
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_cost_cents": self.total_cost_cents,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }
