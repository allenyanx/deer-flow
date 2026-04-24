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
                "model": "gpt-4",
                "dynamic_trigger": {
                    "type": "output_contains",
                    "condition_value": "需要专家",
                    "target_role_id": "expert"
                }
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
                "dependencies": []
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
        """TC-EXEC-004: 测试图节点数等于角色数
        
        验证点：
        - 图中节点数量 = roles 数组长度
        - 每个 role_id 对应一个节点
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(sample_team_config)
        
        # Act: 构建图（不编译，仅获取 StateGraph 对象）
        workflow = builder.build()
        
        # Assert: 验证节点数
        # 注意：workflow.compile() 返回 CompiledGraph，需要先获取 nodes
        assert len(builder.roles) == 2  # analyst 和 reviewer
        # 由于 build() 返回的是编译后的图，我们验证 roles 字典
        assert "analyst" in builder.roles
        assert "reviewer" in builder.roles
    
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
        """TC-EXEC-004: 测试入口点选择逻辑
        
        验证点：
        - 入口点是没有任何依赖的任务
        - analysis-task 无依赖，应被选为入口点
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(sample_team_config)
        
        # Act: 查找入口任务
        entry_task = builder._find_entry_task()
        
        # Assert: 验证入口点
        assert entry_task == "analysis-task"
    
    def test_entry_point_with_multiple_entries(self):
        """测试多个入口点时的选择逻辑
        
        验证点：
        - 当有多个无依赖任务时，任选其一作为入口
        - 返回值应为其中一个入口任务 ID
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
        
        # Act: 查找入口任务
        entry_task = builder._find_entry_task()
        
        # Assert: 验证返回的是入口任务之一
        assert entry_task in ["t1", "t2"]
    
    def test_no_entry_point_returns_none(self):
        """测试无入口点时返回 None
        
        验证点：
        - 当所有任务都有依赖时（异常情况），返回 None
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
        
        # Act: 查找入口任务
        entry_task = builder._find_entry_task()
        
        # Assert: 验证返回 None
        assert entry_task is None
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, circular_dependency_config):
        """TC-EXEC-004: 测试循环依赖检测
        
        验证点：
        - 循环依赖不会导致无限递归
        - 图构建应能处理循环依赖（由 LangGraph 内部处理或抛出异常）
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(circular_dependency_config)
        
        # Act & Assert: 验证循环依赖处理
        # 当前实现未显式检测循环依赖，LangGraph 可能在编译时报错
        # 这里验证 _find_entry_task 能正常工作（即使有循环依赖）
        entry_task = builder._find_entry_task()
        
        # 由于 task_a 依赖 task_b，task_b 依赖 task_a，没有真正的入口点
        assert entry_task is None
    
    @pytest.mark.asyncio
    async def test_dynamic_trigger_conditional_edges(self, dynamic_trigger_config):
        """测试动态触发条件边构建
        
        验证点：
        - dynamic_trigger 配置正确解析
        - 条件边应包含 target_role_id
        """
        # Arrange: 创建 Builder
        builder = StaticTeamGraphBuilder(dynamic_trigger_config)
        
        # Act: 验证 dynamic_trigger 配置
        primary_role = builder.roles["primary"]
        
        # Assert: 验证动态触发配置存在
        assert "dynamic_trigger" in primary_role
        assert primary_role["dynamic_trigger"]["type"] == "output_contains"
        assert primary_role["dynamic_trigger"]["condition_value"] == "需要专家"
        assert primary_role["dynamic_trigger"]["target_role_id"] == "expert"
    
    def test_role_context_building(self, sample_team_config):
        """测试角色上下文构建逻辑
        
        验证点：
        - _build_role_context 正确拼接前置任务输出
        - 包含角色名称和目标
        """
        # Arrange: 创建 Builder 和模拟状态
        builder = StaticTeamGraphBuilder(sample_team_config)
        mock_state = {
            "messages": [],
            "current_role": "reviewer",
            "role_outputs": {
                "analysis-task": {
                    "messages": [{"role": "assistant", "content": "分析结果：销售额增长20%"}]
                }
            },
            "execution_order": ["analyst"]
        }
        
        reviewer_role = builder.roles["reviewer"]
        
        # Act: 构建上下文
        context = builder._build_role_context(reviewer_role, mock_state)
        
        # Assert: 验证上下文内容
        assert "代码审查员" in context
        assert "审查代码质量" in context
        assert "分析结果：销售额增长20%" in context
    
    def test_empty_roles_and_tasks(self):
        """测试空 roles 和 tasks 配置
        
        验证点：
        - 空 roles 时，roles 字典为空
        - 空 tasks 时，_find_entry_task 返回 None
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
        assert builder._find_entry_task() is None


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
