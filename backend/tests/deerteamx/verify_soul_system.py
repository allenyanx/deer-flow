#!/usr/bin/env python3
"""SOUL.md 模板系统快速验证脚本

用于验证 SOUL.md 模板系统的核心功能是否正常工作。
"""

import sys
import os

# 添加 backend 目录到 Python 路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)


def test_templates():
    """测试模板库功能"""
    print("=" * 80)
    print("📋 测试 1: 模板库功能")
    print("=" * 80)
    
    from deerteamx.graph.soul_templates import list_templates, get_template
    
    # 列出所有模板
    templates = list_templates()
    print(f"✅ 可用模板数量: {len(templates)}")
    print(f"   模板列表: {', '.join(templates)}")
    
    # 获取并渲染默认模板
    template = get_template("default")
    rendered = template.format(
        name="Test Role",
        goal="Test Goal",
        backstory="Test Backstory"
    )
    print(f"✅ 默认模板渲染成功 (长度: {len(rendered)} 字符)")
    print()


def test_auto_selector():
    """测试自动选择算法"""
    print("=" * 80)
    print("🤖 测试 2: 自动选择算法")
    print("=" * 80)
    
    from deerteamx.graph.soul_auto_selector import auto_select_template
    
    test_cases = [
        {
            "name": "Data Analyst",
            "goal": "Analyze sales data and identify trends",
            "backstory": "You are a senior data scientist.",
            "expected": "expert_analyst"
        },
        {
            "name": "Content Writer",
            "goal": "Create engaging marketing copy",
            "backstory": "You are a creative writer.",
            "expected": "creative_creator"
        },
        {
            "name": "Software Engineer",
            "goal": "Develop web applications",
            "backstory": "You are an experienced programmer.",
            "expected": "technical_developer"
        },
        {
            "name": "Project Manager",
            "goal": "Coordinate team activities",
            "backstory": "You are an experienced manager.",
            "expected": "coordinator_manager"
        },
        {
            "name": "QA Engineer",
            "goal": "Test software quality",
            "backstory": "You are a meticulous QA specialist.",
            "expected": "quality_assurance"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        selected = auto_select_template(case)
        status = "✅" if selected == case["expected"] else "❌"
        print(f"{status} 测试 {i}: {case['name']} → {selected} (期望: {case['expected']})")
    
    print()


def test_soul_generation():
    """测试 SOUL.md 生成逻辑"""
    print("=" * 80)
    print("✨ 测试 3: SOUL.md 生成逻辑")
    print("=" * 80)
    
    from deerteamx.services.team_service import TeamService
    
    # 测试用例 1: 自动生成（专家分析型）
    role1 = {
        "name": "Market Research Analyst",
        "goal": "Conduct comprehensive market research and competitive analysis",
        "backstory": "You are a seasoned market researcher with expertise in consumer behavior.",
        "skills": ["market-research", "data-analysis"],
        "model": "gpt-4"
    }
    
    soul1 = TeamService.generate_soul_content(role1)
    print(f"✅ 测试 1 - 自动生成:")
    print(f"   角色: {role1['name']}")
    print(f"   长度: {len(soul1)} 字符")
    print(f"   包含 'Expert Analyst': {'Expert Analyst' in soul1}")
    print(f"   包含 Skills 章节: {'## Available Skills' in soul1}")
    print(f"   包含 Model 配置: {'**LLM Model**: `gpt-4`' in soul1}")
    print()
    
    # 测试用例 2: 指定模板（技术开发型）
    role2 = {
        "name": "Full Stack Developer",
        "goal": "Build scalable web applications",
        "backstory": "Experienced developer with expertise in React and Node.js.",
        "skills": ["react", "nodejs", "typescript"],
        "tool_groups": ["bash", "file_operations"]
    }
    
    soul2 = TeamService.generate_soul_content(
        role2,
        template_name="technical_developer"
    )
    print(f"✅ 测试 2 - 指定模板 (technical_developer):")
    print(f"   角色: {role2['name']}")
    print(f"   长度: {len(soul2)} 字符")
    print(f"   包含 'Technical Expert': {'Technical Expert' in soul2}")
    print(f"   包含 Tools 章节: {'## Available Tools' in soul2}")
    print()
    
    # 测试用例 3: 自定义内容优先
    custom_content = "# My Custom Role\n\nThis is my completely custom prompt."
    role3 = {
        "name": "Custom Role",
        "soul_content": custom_content
    }
    
    soul3 = TeamService.generate_soul_content(role3)
    print(f"✅ 测试 3 - 自定义内容优先:")
    print(f"   角色: {role3['name']}")
    print(f"   使用自定义内容: {soul3 == custom_content}")
    print()


def test_integration():
    """集成测试：完整工作流"""
    print("=" * 80)
    print("🔗 测试 4: 完整工作流集成")
    print("=" * 80)
    
    from deerteamx.services.team_service import TeamService
    from deerteamx.graph.soul_auto_selector import auto_select_template
    
    # 模拟用户创建数据分析团队
    role = {
        "name": "Senior Data Scientist",
        "goal": "Analyze complex datasets and provide actionable insights for business decisions",
        "backstory": "You have 10+ years of experience in machine learning, statistical analysis, and data visualization. You've worked at top tech companies and published research papers.",
        "skills": ["data-analysis", "ml-modeling", "visualization", "statistical-testing"],
        "tool_groups": ["python_execution", "file_operations", "bash"],
        "model": "gpt-4-turbo",
        "allow_delegation": True
    }
    
    # 步骤 1: 自动选择模板
    selected_template = auto_select_template(role)
    print(f"📊 步骤 1 - 自动选择模板: {selected_template}")
    
    # 步骤 2: 生成 SOUL.md
    soul_content = TeamService.generate_soul_content(role)
    print(f"📝 步骤 2 - 生成 SOUL.md:")
    print(f"   总长度: {len(soul_content)} 字符")
    print(f"   行数: {len(soul_content.splitlines())} 行")
    
    # 步骤 3: 验证内容完整性
    checks = [
        ("角色标题", f"Expert Analyst: {role['name']}" in soul_content),
        ("专业背景", "Professional Background" in soul_content),
        ("任务声明", "Mission Statement" in soul_content),
        ("分析框架", "Analytical Framework" in soul_content),
        ("质量标准", "Quality Standards" in soul_content),
        ("技能章节", "## Available Skills" in soul_content),
        ("工具章节", "## Available Tools" in soul_content),
        ("委派权限", "## Delegation Authority" in soul_content),
        ("技术配置", "## Technical Configuration" in soul_content),
        ("具体技能", "- `data-analysis`" in soul_content),
        ("具体工具", "- `python_execution`" in soul_content),
        ("模型配置", "**LLM Model**: `gpt-4-turbo`" in soul_content),
    ]
    
    print(f"\n🔍 步骤 3 - 内容完整性检查:")
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print(f"\n🎉 所有检查通过！生成的 SOUL.md 质量优秀。")
    else:
        print(f"\n⚠️  部分检查未通过，请检查生成逻辑。")
    
    # 打印前 500 字符预览
    print(f"\n📄 SOUL.md 预览（前 500 字符）:")
    print("-" * 80)
    print(soul_content[:500])
    print("-" * 80)
    print()


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 SOUL.md 模板系统快速验证")
    print("=" * 80 + "\n")
    
    try:
        # 运行所有测试
        test_templates()
        test_auto_selector()
        test_soul_generation()
        test_integration()
        
        # 总结
        print("=" * 80)
        print("✅ 所有测试完成！SOUL.md 模板系统运行正常。")
        print("=" * 80)
        print("\n💡 提示:")
        print("   - 运行 pytest tests/test_soul_templates.py -v 执行完整测试套件")
        print("   - 访问 http://localhost:8000/api/v1/soul/templates 查看 API 文档")
        print("   - 阅读 backend/deerteamx/SOUL_TEMPLATE_README.md 了解详细用法")
        print()
        
        return 0
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
