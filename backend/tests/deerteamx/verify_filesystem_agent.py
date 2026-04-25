#!/usr/bin/env python3
"""
验证 _ensure_custom_agent_exists 切换到文件系统方案后的功能
"""

import asyncio
import tempfile
from pathlib import Path
import yaml


async def test_ensure_custom_agent_filesystem():
    """测试 Agent 配置是否正确写入文件系统"""
    
    print("=" * 80)
    print("测试: _ensure_custom_agent_exists (文件系统方案)")
    print("=" * 80)
    
    # 创建临时目录作为 Agents 根目录
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_root = Path(tmpdir)
        
        # Mock get_paths
        from unittest.mock import patch, MagicMock
        
        mock_paths = MagicMock()
        mock_paths.agent_dir = lambda name: agents_root / name
        
        with patch('deerflow.config.paths.get_paths', return_value=mock_paths):
            from deerteamx.graph.builder import StaticTeamGraphBuilder
            
            # 准备测试角色配置
            role = {
                "role_id": "test-analyst",
                "agent_name": "test-analyst",
                "name": "Data Analyst",
                "description": "专业数据分析师",
                "goal": "分析销售数据并提供洞察",
                "backstory": "你是一位资深数据科学家，拥有10年以上的统计分析经验。",
                "model": "gpt-4",
                "skills": ["data-analysis", "chart-visualization"],
                "tool_groups": ["bash", "python_execution"],
                "allow_delegation": True,
            }
            
            # 创建 Builder
            builder = StaticTeamGraphBuilder({
                "name": "Test Team",
                "roles": [role],
                "tasks": []
            })
            
            # 执行 _ensure_custom_agent_exists
            await builder._ensure_custom_agent_exists("test-analyst", role)
            
            # ========== 验证 config.yaml ==========
            config_file = agents_root / "test-analyst" / "config.yaml"
            assert config_file.exists(), f"❌ config.yaml 不存在: {config_file}"
            print(f"✅ config.yaml 已创建: {config_file}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print("\n📄 config.yaml 内容:")
            print(yaml.dump(config, default_flow_style=False, allow_unicode=True))
            
            assert config["name"] == "test-analyst"
            assert config["model"] == "gpt-4"
            assert config["skills"] == ["data-analysis", "chart-visualization"]
            assert config["tool_groups"] == ["bash", "python_execution"]
            print("✅ config.yaml 内容正确")
            
            # ========== 验证 SOUL.md ==========
            soul_file = agents_root / "test-analyst" / "SOUL.md"
            assert soul_file.exists(), f"❌ SOUL.md 不存在: {soul_file}"
            print(f"\n✅ SOUL.md 已创建: {soul_file}")
            
            soul_content = soul_file.read_text(encoding='utf-8')
            print(f"\n📄 SOUL.md 长度: {len(soul_content)} 字符")
            print(f"\n📄 SOUL.md 前500字符:\n{soul_content[:500]}...")
            
            # 验证关键内容
            assert "Data Analyst" in soul_content
            assert "分析销售数据并提供洞察" in soul_content
            assert "Available Skills" in soul_content
            assert "data-analysis" in soul_content
            assert "Delegation Authority" in soul_content  # allow_delegation=True
            print("✅ SOUL.md 内容正确（包含动态章节）")
            
            # ========== 测试自定义 soul_content 优先 ==========
            print("\n" + "=" * 80)
            print("测试: 自定义 soul_content 优先策略")
            print("=" * 80)
            
            custom_role = {
                **role,
                "soul_content": "# My Custom Role\n\nThis is my custom system prompt."
            }
            
            await builder._ensure_custom_agent_exists("test-custom", custom_role)
            
            custom_soul_file = agents_root / "test-custom" / "SOUL.md"
            custom_content = custom_soul_file.read_text(encoding='utf-8')
            
            assert custom_content == "# My Custom Role\n\nThis is my custom system prompt."
            print("✅ 自定义 soul_content 优先策略生效")
            
            # ========== 测试模板指定 ==========
            print("\n" + "=" * 80)
            print("测试: 指定模板名称")
            print("=" * 80)
            
            template_role = {
                **role,
                "soul_template": "creative_creator",
            }
            
            await builder._ensure_custom_agent_exists("test-template", template_role)
            
            template_soul_file = agents_root / "test-template" / "SOUL.md"
            template_content = template_soul_file.read_text(encoding='utf-8')
            
            assert "Creative Specialist" in template_content
            assert "Creative Process" in template_content
            print("✅ 指定模板名称策略生效")
    
    print("\n" + "=" * 80)
    print("🎉 所有测试通过！文件系统方案工作正常。")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ensure_custom_agent_filesystem())
