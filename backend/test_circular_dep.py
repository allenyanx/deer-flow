#!/usr/bin/env python3
"""循环依赖检测功能快速验证脚本"""

import sys
sys.path.insert(0, '/home/ycp/workSpace/ai/games_dev/deer-flow/backend')

from deerteamx.graph.builder import StaticTeamGraphBuilder

def test_simple_cycle():
    """测试简单循环（2个任务）"""
    print("\n=== 测试1: 简单循环 (task_a <-> task_b) ===")
    config = {
        "name": "循环团队",
        "execution_mode": "static",
        "roles": [
            {"role_id": "r1", "agent_name": "a1", "name": "R1", "goal": "G1", "model": "gpt-4"},
            {"role_id": "r2", "agent_name": "a2", "name": "R2", "goal": "G2", "model": "gpt-4"}
        ],
        "tasks": [
            {"task_id": "task_a", "description": "A", "expected_output": "O", "assigned_role": "r1", "dependencies": ["task_b"]},
            {"task_id": "task_b", "description": "B", "expected_output": "O", "assigned_role": "r2", "dependencies": ["task_a"]}
        ],
        "global_settings": {"process_type": "sequential"}
    }
    
    builder = StaticTeamGraphBuilder(config)
    try:
        builder.build()
        print("❌ 失败: 应该抛出 ValueError")
        return False
    except ValueError as e:
        print(f"✅ 成功检测到循环依赖")
        print(f"错误信息: {str(e)[:200]}...")
        return True

def test_complex_cycle():
    """测试复杂循环（3个任务）"""
    print("\n=== 测试2: 复杂循环 (task_a -> task_b -> task_c -> task_a) ===")
    config = {
        "name": "复杂循环团队",
        "execution_mode": "static",
        "roles": [
            {"role_id": "r1", "agent_name": "a1", "name": "R1", "goal": "G1", "model": "gpt-4"},
            {"role_id": "r2", "agent_name": "a2", "name": "R2", "goal": "G2", "model": "gpt-4"},
            {"role_id": "r3", "agent_name": "a3", "name": "R3", "goal": "G3", "model": "gpt-4"}
        ],
        "tasks": [
            {"task_id": "task_a", "description": "A", "expected_output": "O", "assigned_role": "r1", "dependencies": ["task_c"]},
            {"task_id": "task_b", "description": "B", "expected_output": "O", "assigned_role": "r2", "dependencies": ["task_a"]},
            {"task_id": "task_c", "description": "C", "expected_output": "O", "assigned_role": "r3", "dependencies": ["task_b"]}
        ],
        "global_settings": {"process_type": "sequential"}
    }
    
    builder = StaticTeamGraphBuilder(config)
    try:
        builder.build()
        print("❌ 失败: 应该抛出 ValueError")
        return False
    except ValueError as e:
        print(f"✅ 成功检测到循环依赖")
        error_msg = str(e)
        if "task_a" in error_msg and "task_b" in error_msg and "task_c" in error_msg:
            print(f"✅ 错误信息包含所有任务: task_a, task_b, task_c")
        return True

def test_no_cycle():
    """测试无循环的正常配置"""
    print("\n=== 测试3: 正常 DAG (无循环) ===")
    config = {
        "name": "正常团队",
        "execution_mode": "static",
        "roles": [
            {"role_id": "analyst", "agent_name": "data_analyst_v1", "name": "数据分析师", "goal": "分析数据", "model": "gpt-4"},
            {"role_id": "reviewer", "agent_name": "code_reviewer_v1", "name": "代码审查员", "goal": "审查代码", "model": "gpt-4"}
        ],
        "tasks": [
            {"task_id": "analysis-task", "description": "分析数据", "expected_output": "报告", "assigned_role": "analyst", "dependencies": []},
            {"task_id": "review-task", "description": "审查报告", "expected_output": "意见", "assigned_role": "reviewer", "dependencies": ["analysis-task"]}
        ],
        "global_settings": {"process_type": "sequential"}
    }
    
    builder = StaticTeamGraphBuilder(config)
    cycle = builder._detect_circular_dependencies()
    
    if cycle is None:
        print("✅ 正确识别为无循环")
        try:
            workflow = builder.build()
            print("✅ 图构建成功")
            return True
        except Exception as e:
            print(f"❌ 图构建失败: {e}")
            return False
    else:
        print(f"❌ 错误检测到循环: {cycle}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("循环依赖检测功能验证")
    print("=" * 80)
    
    results = []
    results.append(("简单循环检测", test_simple_cycle()))
    results.append(("复杂循环检测", test_complex_cycle()))
    results.append(("正常DAG检测", test_no_cycle()))
    
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + ("=" * 80))
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败")
    print("=" * 80)
    
    sys.exit(0 if all_passed else 1)
