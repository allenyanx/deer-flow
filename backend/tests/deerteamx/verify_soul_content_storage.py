#!/usr/bin/env python3
"""
验证 soul_content 字段在数据库中的存储和读取
"""

import asyncio
import json
from uuid import uuid4


async def verify_soul_content_storage():
    """验证 soul_content 是否正确存储到数据库"""
    
    print("=" * 80)
    print("测试: soul_content 字段存储验证")
    print("=" * 80)
    
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from deerteamx.models.base import Team, User
    from deerteamx.api.schemas.team_schemas import RoleConfig, TaskConfig, GlobalSettings
    
    # 创建数据库连接
    engine = create_async_engine(
        "postgresql+asyncpg://deerteamx_user:password@localhost:5432/deerteamx_db",
        echo=False
    )
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # ========== 1. 创建测试用户 ==========
        test_user_id = uuid4()
        test_user = User(
            user_id=test_user_id,
            username=f"test_user_{test_user_id.hex[:8]}",
            password_hash="dummy_hash",
            role_type="developer"
        )
        db.add(test_user)
        await db.flush()
        print(f"✅ 创建测试用户: {test_user.username}")
        
        # ========== 2. 创建包含 soul_content 的角色配置 ==========
        role_with_soul = RoleConfig(
            role_id="analyst-001",
            agent_name="data-analyst-test",
            name="Data Analyst",
            goal="分析销售数据并提供洞察",
            backstory="你是一位资深数据科学家，拥有10年以上的统计分析经验。",
            soul_content="# Custom SOUL.md\n\nThis is my custom system prompt for data analysis.",
            model="gpt-4",
            skills=["data-analysis"],
            tool_groups=["bash"],
        )
        
        role_without_soul = RoleConfig(
            role_id="writer-001",
            agent_name="report-writer-test",
            name="Report Writer",
            goal="撰写专业报告",
            backstory="你是一位专业的报告撰写专家。",
            # 注意：没有 soul_content 字段
            model="claude-3-opus",
        )
        
        print(f"\n📄 Role 1 (有 soul_content):")
        print(json.dumps(role_with_soul.model_dump(), indent=2, ensure_ascii=False))
        
        print(f"\n📄 Role 2 (无 soul_content):")
        print(json.dumps(role_without_soul.model_dump(), indent=2, ensure_ascii=False))
        
        # ========== 3. 创建团队配置 ==========
        team_id = f"test-team-{uuid4().hex[:8]}"
        config_snapshot = {
            "name": "Test Team with SOUL",
            "description": "测试 soul_content 存储",
            "execution_mode": "static",
            "roles": [
                role_with_soul.model_dump(),
                role_without_soul.model_dump()
            ],
            "tasks": [
                TaskConfig(
                    task_id="task-001",
                    description="分析数据",
                    expected_output="数据分析报告",
                    assigned_role="analyst-001"
                ).model_dump()
            ],
            "global_settings": GlobalSettings(process_type="sequential").model_dump()
        }
        
        # ========== 4. 保存到数据库 ==========
        team = Team(
            team_id=team_id,
            name="Test Team with SOUL",
            description="测试 soul_content 存储",
            execution_mode="static",
            status="draft",
            creator_id=test_user_id,
            current_version="v0.1.0",
            config_snapshot=config_snapshot
        )
        
        db.add(team)
        await db.commit()
        print(f"\n✅ 团队创建成功: {team_id}")
        
        # ========== 5. 从数据库读取并验证 ==========
        from sqlalchemy import select
        
        stmt = select(Team).where(Team.team_id == team_id)
        result = await db.execute(stmt)
        retrieved_team = result.scalar_one()
        
        print(f"\n📖 从数据库读取团队配置...")
        
        # 验证 roles 中的 soul_content
        roles = retrieved_team.config_snapshot["roles"]
        
        print(f"\n🔍 验证 Role 1 (analyst-001):")
        analyst_role = next(r for r in roles if r["role_id"] == "analyst-001")
        assert "soul_content" in analyst_role, "❌ soul_content 字段丢失！"
        assert analyst_role["soul_content"] == "# Custom SOUL.md\n\nThis is my custom system prompt for data analysis."
        print(f"✅ soul_content 存在且内容正确")
        print(f"   内容长度: {len(analyst_role['soul_content'])} 字符")
        print(f"   前100字符: {analyst_role['soul_content'][:100]}...")
        
        print(f"\n🔍 验证 Role 2 (writer-001):")
        writer_role = next(r for r in roles if r["role_id"] == "writer-001")
        assert "soul_content" in writer_role, "❌ soul_content 字段不存在（应该是 None）"
        assert writer_role["soul_content"] is None, "❌ soul_content 应该是 None"
        print(f"✅ soul_content 为 None（符合预期）")
        
        # ========== 6. 清理测试数据 ==========
        print(f"\n🧹 清理测试数据...")
        await db.delete(retrieved_team)
        await db.delete(test_user)
        await db.commit()
        print(f"✅ 测试数据已清理")
    
    print("\n" + "=" * 80)
    print("🎉 所有验证通过！soul_content 字段正确存储和读取。")
    print("=" * 80)
    print("\n💡 结论:")
    print("   - soul_content 字段存储在 Team.config_snapshot JSONB 中")
    print("   - 通过 RoleConfig Pydantic Schema 自动序列化/反序列化")
    print("   - 不需要单独的数据库列")


if __name__ == "__main__":
    asyncio.run(verify_soul_content_storage())
