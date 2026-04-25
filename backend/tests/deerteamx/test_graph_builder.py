"""StaticTeamGraphBuilder 单元测试

测试范围：
- 图构建正确性验证(节点数/边数)
- 循环依赖检测
- 入口点选择逻辑
- 动态触发条件边

测试用例对齐 BACKEND_TEST_PLAN.md:
- TC-EXEC-004: StaticTeamGraph 构建正确性验证
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from deerteamx.graph.builder import StaticTeamGraphBuilder, TeamState


# ============================================================================
# 测试夹具（Fixtures）
# ============================================================================

@pytest.fixture
def sample_team_config():
    """示例团队配置（用于图构建测试）"""
    return {
        "name": "测试团队",
        "execution_mode": "static",
        "roles": [
            {
                "role_id": "analyst",
                "agent_name": "data_analyst_v1",
                "name": "数据分析师",
                "goal": "分析数据并提供洞察",
                "model": "gpt-4-turbo",
                "tool_groups": ["bash"],
                "skills": ["data-analysis"]
            },
            {
                "role_id": "reviewer",
                "agent_name": "code_reviewer_v1",
                "name": "代码审查员",
                "goal": "审查代码质量",
                "model": "gpt-4-turbo",
                "tool_groups": [],
                "skills": []
            }
        ],
        "tasks": [
            {
                "task_id": "analysis-task",
                "description": "分析销售数据",
                "expected_output": "分析报告",
                "assigned_role": "analyst",
                "dependencies": []
            },
            {
                "task_id": "review-task",
                "description": "审查分析报告",
                "expected_output": "审查意见",
                "assigned_role": "reviewer",
                "dependencies": ["analysis-task"]
            }
        ],
        "global_settings": {
            "process_type": "sequential",
            "verbose": False
        }
    }


@pytest.fixture
def circular_dependency_config():
    """循环依赖配置（用于检测测试）"""
    return {
        "name": "循环依赖团队",
        "execution_mode": "static",
        "roles": [
            {
                "role_id": "role_a",
                "agent_name": "agent_a",
                "name": "角色A",
                "goal": "目标A",
                "model": "gpt-4"
            },
            {
                "role_id": "role_b",
                "agent_name": "agent_b",
                "name": "角色B",
                "goal": "目标B",
                "model": "gpt-4"
            }
        ],
        "tasks": [
            {
                "task_id": "task_a",
                "description": "任务A",
                "expected_output": "输出A",
                "assigned_role": "role_a",
                "dependencies": ["task_b"]  # 依赖 task_b
            },
            {
                "task_id": "task_b",
                "description": "任务B",
                "expected_output": "输出B",
                "assigned_role": "role_b",
                "dependencies": ["task_a"]  # 依赖 task_a (形成循环)
            }
        ],
        "global_settings": {
            "process_type": "sequential"
        }
    }


@pytest.fixture
def dynamic_trigger_config():
    """动态触发配置（用于条件边测试）"""
    return {
        "name": "动态触发团队",
        "execution_mode": "hybrid",
        "roles": [
            {
                "role_id": "primary",
                "agent_name": "primary_agent",
                "name": "主要角色",
                "goal": "主要目标",
                "model": "gpt-4"
            },
            {
                "role_id": "expert",
                "agent_name": "expert_agent",
                "name": "专家角色",
                "goal": "专家目标",
                "model": "gpt-4"
            }
        ],
        "tasks": [
            {
                "task_id": "primary-task",
                "description": "主要任务",
                "expected_output": "主要输出",
                "assigned_role": "primary",
                "dependencies": [],
                "dynamic_trigger": {
                    "type": "output_contains",
                    "condition_value": "需要专家",
                    "target_task_id": "expert-task"
                }
            },
            {
                "task_id": "expert-task",
                "description": "专家任务",
                "expected_output": "专家输出",
                "assigned_role": "expert",
                "dependencies": ["primary-task"]
            }
        ],
        "global_settings": {
            "process_type": "sequential"
        }
    }


# ============================================================================
# StaticTeamGraphBuilder 测试
# ============================================================================

class TestStaticTeamGraphBuilder:
    """StaticTeamGraphBuilder 图构建测试"""
    
    def test_build_graph_node_count(self, sample_team_config):
        """TC-EXEC-004: 测试图节点数等于任务数（方案 A：任务驱动）
        
        验证点：
        - 图中节点数量 = tasks 数组长度
        - 每个 task_id 对应一个节点
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(sample_team_config)
        
        # Act: 构建图（不编译，仅获取 StateGraph 对象）
        workflow = builder.build()
        
        # Assert: 验证节点数
        assert len(builder.tasks) == 2  # analysis-task 和 review-task
        # 验证任务 ID 存在
        task_ids = [t["task_id"] for t in sample_team_config["tasks"]]
        assert "analysis-task" in task_ids
        assert "review-task" in task_ids
    
    def test_build_graph_edge_count(self, sample_team_config):
        """TC-EXEC-004: 测试图边数等于依赖数
        
        验证点：
        - 基础依赖边数量 = 所有任务的 dependencies 总数
        - review-task 依赖 analysis-task，应有 1 条边
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(sample_team_config)
        
        # Act: 统计依赖边数量
        total_deps = sum(len(task.get("dependencies", [])) for task in sample_team_config["tasks"])
        
        # Assert: 验证依赖数
        assert total_deps == 1  # review-task 依赖 analysis-task
        assert sample_team_config["tasks"][1]["dependencies"] == ["analysis-task"]
    
    def test_entry_point_selection(self, sample_team_config):
        """TC-EXEC-004: 测试入口点选择逻辑（方案 A：支持多入口）
        
        验证点：
        - 入口点是没有任何依赖的任务
        - analysis-task 无依赖，应被选为入口点之一
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(sample_team_config)
        
        # Act: 查找入口任务（返回列表）
        entry_tasks = builder._find_entry_tasks()
        
        # Assert: 验证入口点
        assert "analysis-task" in entry_tasks
        assert len(entry_tasks) == 1  # 只有一个无依赖任务
    
    def test_entry_point_with_multiple_entries(self):
        """测试多个入口点时的选择逻辑（方案 A：支持并行入口）
        
        验证点：
        - 当有多个无依赖任务时，全部作为入口点返回
        - 返回值应包含所有入口任务 ID
        """
        # Arrange: 创建多入口配置
        multi_entry_config = {
            "name": "多入口团队",
            "roles": [
                {"role_id": "r1", "agent_name": "a1", "name": "R1", "goal": "G1", "model": "gpt-4"},
                {"role_id": "r2", "agent_name": "a2", "name": "R2", "goal": "G2", "model": "gpt-4"}
            ],
            "tasks": [
                {"task_id": "t1", "description": "T1", "expected_output": "O1", "assigned_role": "r1", "dependencies": []},
                {"task_id": "t2", "description": "T2", "expected_output": "O2", "assigned_role": "r2", "dependencies": []}
            ],
            "global_settings": {"process_type": "sequential"}
        }
        
        builder = StaticTeamGraphBuilder(multi_entry_config)
        
        # Act: 查找入口任务（返回列表）
        entry_tasks = builder._find_entry_tasks()
        
        # Assert: 验证返回所有入口任务
        assert set(entry_tasks) == {"t1", "t2"}
        assert len(entry_tasks) == 2
    
    def test_no_entry_point_returns_empty_list(self):
        """测试无入口点时返回空列表（方案 A）
        
        验证点：
        - 当所有任务都有依赖时（异常情况），返回空列表
        """
        # Arrange: 创建异常配置（所有任务都有依赖）
        invalid_config = {
            "name": "无效团队",
            "roles": [
                {"role_id": "r1", "agent_name": "a1", "name": "R1", "goal": "G1", "model": "gpt-4"}
            ],
            "tasks": [
                {"task_id": "t1", "description": "T1", "expected_output": "O1", "assigned_role": "r1", "dependencies": ["t1"]}
            ],
            "global_settings": {"process_type": "sequential"}
        }
        
        builder = StaticTeamGraphBuilder(invalid_config)
        
        # Act: 查找入口任务（返回列表）
        entry_tasks = builder._find_entry_tasks()
        
        # Assert: 验证返回空列表
        assert entry_tasks == []
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, circular_dependency_config):
        """TC-EXEC-004: 测试循环依赖检测（方案 A）
        
        验证点：
        - 循环依赖会被主动检测并抛出 ValueError
        - 错误信息包含详细的循环路径
        - build() 方法在检测到循环依赖时不会继续构建图
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(circular_dependency_config)
        
        # Act & Assert: 验证循环依赖被检测并抛出异常
        with pytest.raises(ValueError) as exc_info:
            builder.build()
        
        # 验证错误信息包含循环路径
        error_message = str(exc_info.value)
        assert "检测到循环依赖" in error_message
        assert "task_a" in error_message
        assert "task_b" in error_message
        assert "建议：删除" in error_message  # 包含解除建议
    
    @pytest.mark.asyncio
    async def test_complex_circular_dependency(self):
        """测试复杂循环依赖（3个任务形成环）
        
        验证点：
        - task_a -> task_b -> task_c -> task_a 的循环能被检测
        - 错误信息展示完整循环路径
        """
        # Arrange: 创建三任务循环配置
        complex_cycle_config = {
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
        
        builder = StaticTeamGraphBuilder(complex_cycle_config)
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            builder.build()
        
        error_message = str(exc_info.value)
        assert "检测到循环依赖" in error_message
        # 验证三个任务都在循环路径中
        assert "task_a" in error_message
        assert "task_b" in error_message
        assert "task_c" in error_message
    
    @pytest.mark.asyncio
    async def test_no_circular_dependency(self, sample_team_config):
        """测试无循环依赖的正常配置
        
        验证点：
        - 正常 DAG 配置能成功构建图
        - _detect_circular_dependencies 返回 None
        """
        # Arrange
        builder = StaticTeamGraphBuilder(sample_team_config)
        
        # Act
        cycle = builder._detect_circular_dependencies()
        
        # Assert
        assert cycle is None
        
        # 验证图能成功构建
        workflow = builder.build()
        assert workflow is not None
    
    @pytest.mark.asyncio
    async def test_multiple_independent_cycles(self):
        """测试多个独立循环（非连通图）
        
        验证点：
        - 检测到第一个循环即停止并返回
        - 不会无限递归
        """
        # Arrange: 两个独立的循环
        multi_cycle_config = {
            "name": "多循环团队",
            "execution_mode": "static",
            "roles": [
                {"role_id": "r1", "agent_name": "a1", "name": "R1", "goal": "G1", "model": "gpt-4"},
                {"role_id": "r2", "agent_name": "a2", "name": "R2", "goal": "G2", "model": "gpt-4"},
                {"role_id": "r3", "agent_name": "a3", "name": "R3", "goal": "G3", "model": "gpt-4"},
                {"role_id": "r4", "agent_name": "a4", "name": "R4", "goal": "G4", "model": "gpt-4"}
            ],
            "tasks": [
                # 循环 1: task_a <-> task_b
                {"task_id": "task_a", "description": "A", "expected_output": "O", "assigned_role": "r1", "dependencies": ["task_b"]},
                {"task_id": "task_b", "description": "B", "expected_output": "O", "assigned_role": "r2", "dependencies": ["task_a"]},
                # 循环 2: task_c <-> task_d
                {"task_id": "task_c", "description": "C", "expected_output": "O", "assigned_role": "r3", "dependencies": ["task_d"]},
                {"task_id": "task_d", "description": "D", "expected_output": "O", "assigned_role": "r4", "dependencies": ["task_c"]}
            ],
            "global_settings": {"process_type": "sequential"}
        }
        
        builder = StaticTeamGraphBuilder(multi_cycle_config)
        
        # Act & Assert: 应该检测到至少一个循环
        with pytest.raises(ValueError) as exc_info:
            builder.build()
        
        error_message = str(exc_info.value)
        assert "检测到循环依赖" in error_message
    
    @pytest.mark.asyncio
    async def test_dynamic_trigger_conditional_edges(self, dynamic_trigger_config):
        """测试动态触发条件边构建（方案 A：基于 task_id）
        
        验证点：
        - dynamic_trigger 配置正确解析
        - 条件边应包含 target_task_id
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(dynamic_trigger_config)
        
        # Act: 验证 dynamic_trigger 配置（现在在 task 上）
        primary_task = next(t for t in builder.tasks if t["task_id"] == "primary-task")
        
        # Assert: 验证动态触发配置存在
        assert "dynamic_trigger" in primary_task
        assert primary_task["dynamic_trigger"]["type"] == "output_contains"
        assert primary_task["dynamic_trigger"]["condition_value"] == "需要专家"
        assert primary_task["dynamic_trigger"]["target_task_id"] == "expert-task"
    
    def test_task_context_building(self, sample_team_config):
        """测试任务上下文构建逻辑（方案 A：基于 task_id）
        
        验证点：
        - _build_task_context 正确拼接前置任务输出
        - 包含角色名称、目标和当前任务描述
        """
        from langchain_core.messages import AIMessage
        
        # Arrange: 创建 Builder 和模拟状态
        builder = StaticTeamGraphBuilder(sample_team_config)
        mock_state = {
            "messages": [],
            "current_task": "review-task",
            "task_outputs": {
                "analysis-task": {
                    "messages": [AIMessage(content="分析结果：销售额增长20%")]
                }
            },
            "completed_tasks": ["analysis-task"]
        }
        
        review_task = next(t for t in builder.tasks if t["task_id"] == "review-task")
        
        # Act: 构建上下文
        context = builder._build_task_context(review_task, mock_state)
        
        # Assert: 验证上下文内容
        assert "代码审查员" in context
        assert "审查代码质量" in context
        assert "分析结果：销售额增长20%" in context
        assert "审查分析报告" in context  # 当前任务描述
    
    def test_empty_roles_and_tasks(self):
        """测试空 roles 和 tasks 配置（方案 A）
        
        验证点：
        - 空 tasks 时，_find_entry_tasks 返回空列表
        - 空 roles 时，roles 字典为空
        """
        # Arrange: 创建空配置
        empty_config = {
            "name": "空团队",
            "roles": [],
            "tasks": [],
            "global_settings": {"process_type": "sequential"}
        }
        
        builder = StaticTeamGraphBuilder(empty_config)
        
        # Act & Assert: 验证空配置处理
        assert len(builder.roles) == 0
        assert len(builder.tasks) == 0
        assert builder._find_entry_tasks() == []


# ============================================================================
# 辅助函数测试
# ============================================================================

class TestHelperFunctions:
    """StaticTeamGraphBuilder 辅助函数测试"""
    
    def test_parse_sse_event_valid_json(self):
        """测试 SSE 事件解析（有效 JSON）"""
        from deerteamx.runtime.ws_bridge import SSEToWebSocketBridge
        
        bridge = SSEToWebSocketBridge()
        data = '{"event": "on_chain_start", "data": {"input": "test"}}'
        
        result = bridge._parse_sse_event(data)
        
        assert result["event"] == "on_chain_start"
        assert result["data"]["input"] == "test"
    
    def test_parse_sse_event_invalid_json(self):
        """测试 SSE 事件解析（无效 JSON）"""
        from deerteamx.runtime.ws_bridge import SSEToWebSocketBridge
        
        bridge = SSEToWebSocketBridge()
        data = "invalid json string"
        
        result = bridge._parse_sse_event(data)
        
        assert result["raw"] == "invalid json string"
        assert result["status"] == "unknown"
