# DeerTeamX 团队管理集成测试

## 📋 概述

本目录包含DeerTeamX团队管理模块的**集成测试**，直接使用真实的PostgreSQL和Redis服务进行验证。

## 🎯 测试文件

- **`test_team_management_integration.py`**: 22个集成测试用例，覆盖团队CRUD、权限控制、版本管理等核心功能

## 🚀 快速开始

### 1. 前置条件

确保以下服务已启动并运行：

```bash
# 检查 PostgreSQL
psql -h localhost -p 5433 -U deerteamx_user -d deerteamx_db -c "SELECT 1;"

# 检查 Redis
redis-cli -h localhost -p 6379 ping
```

### 2. 运行测试

```bash
# 进入后端目录
cd /home/ycp/workSpace/ai/games_dev/deer-flow/backend

# 运行所有团队管理集成测试
uv run pytest tests/deerteamx/test_team_management_integration.py -v

# 生成覆盖率报告
uv run pytest tests/deerteamx/test_team_management_integration.py \
  --cov=deerteamx.services.team_service \
  --cov-report=html \
  -v
```

## 📊 测试覆盖

| 测试类 | 用例数 | 覆盖功能 |
|--------|-------|---------|
| `TestCreateTeam` | 5 | 团队创建、名称唯一性、版本快照 |
| `TestGetTeam` | 6 | 团队查询、分页、筛选、权限校验 |
| `TestUpdateTeam` | 4 | 团队更新、乐观锁、部分更新 |
| `TestDeleteTeam` | 2 | 软删除、执行中拦截 |
| `TestCheckNameAvailability` | 2 | 名称检查、建议名称生成 |
| `TestHelperMethods` | 3 | 辅助方法验证 |
| **总计** | **22** | **100%核心逻辑覆盖** |

## 🔑 关键特性

✅ **真实数据库操作**: 所有测试直接写入PostgreSQL  
✅ **事务隔离**: 每个测试结束后自动回滚，互不影响  
✅ **数据完整性验证**: 通过SQL查询验证数据库状态  
✅ **中文注释**: 所有测试用例都有清晰的中文说明  
✅ **AAA模式**: 严格遵循Arrange-Act-Assert测试模式  

## 📝 测试示例

```python
@pytest.mark.asyncio
async def test_create_team_success(self, team_service, sample_team_data, test_user):
    """TC-TEAM-IT-001: 测试成功创建团队"""
    # Act: 执行创建
    team = await team_service.create_team(
        team_data=sample_team_data,
        user_id=test_user.user_id
    )
    
    # Assert: 验证结果
    assert team.name == sample_team_data["name"]
    assert team.status == "draft"
    assert team.current_version == "v0.1.0"
```

## 🔧 故障排查

### 问题1: 数据库连接失败

```bash
# 检查 .env.deerteamx 配置
cat .env.deerteamx | grep DATABASE_URL

# 手动连接测试
psql -h localhost -p 5433 -U deerteamx_user -d deerteamx_db
```

### 问题2: 表结构不存在

测试框架会自动创建表结构。如果失败，请手动初始化：

```python
# 在Python中执行
from deerteamx.database.session import init_db
import asyncio
asyncio.run(init_db())
```

### 问题3: 测试数据残留

每个测试结束后会自动回滚。如果仍有残留数据：

```sql
-- 清空测试数据
TRUNCATE TABLE teams, team_versions, executions CASCADE;
```

## 📚 相关文档

- [测试覆盖分析文档](../../../docs/deer-teamx-docs/TEST_COVERAGE_ANALYSIS_TEAM_MANAGEMENT.md)
- [API参考文档](../../../docs/deer-teamx-docs/API_REFERENCE.md)
- [架构设计文档](../../../docs/deer-teamx-docs/ARCHITECTURE_DESIGN.md)

---

**最后更新**: 2026-04-24  
**维护者**: DeerTeamX 开发团队
