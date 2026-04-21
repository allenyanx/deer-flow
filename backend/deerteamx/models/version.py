"""DeerTeamX 团队版本数据模型。

该模块定义了团队配置快照在 PostgreSQL 中的存储结构，
支持语义化版本管理及配置差异对比。
"""

from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from deerteamx.database import Base


class TeamVersion(Base):
    """团队配置版本快照模型。"""
    
    __tablename__ = "team_versions"

    # 主键：自增 ID
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 外键：关联的团队配置
    team_id = Column(String(64), ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 语义化版本号 (e.g., v1.0.0, v1.1.2)
    version_tag = Column(String(20), nullable=False)
    
    # 版本类型: major, minor, patch
    change_type = Column(String(10), nullable=False, default="patch")
    
    # 配置内容快照 (JSONB)
    config_snapshot = Column(JSON, nullable=False)
    
    # 变更说明
    commit_message = Column(Text, nullable=True)
    
    # 审计字段
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    team = relationship("Team", back_populates="versions")

    def to_dict(self) -> dict:
        """将模型转换为字典以便 API 响应。"""
        return {
            "id": self.id,
            "team_id": self.team_id,
            "version_tag": self.version_tag,
            "change_type": self.change_type,
            "commit_message": self.commit_message,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # 注意：config_snapshot 通常在详情接口中返回，列表接口可省略以优化性能
        }
