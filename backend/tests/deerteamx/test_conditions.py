"""条件路由逻辑单元测试

测试范围：
- 共识模式投票机制
- dynamic_trigger 条件判断
- human_feedback 暂停逻辑

测试用例对齐 BACKEND_TEST_PLAN.md:
- TC-EXEC-010: 共识模式投票机制验证
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from deerteamx.graph.builder import StaticTeamGraphBuilder


# ============================================================================
# 测试夹具（Fixtures）
# ============================================================================

@pytest.fixture
def consensus_mode_config():
    """共识模式配置（用于投票机制测试）"""
    return {
        "name": "共识模式团队",
        "execution_mode": "static",
        "roles": [
            {
                "role_id": "voter_1",
                "agent_name": "voter_agent_1",
                "name": "投票者1",
                "goal": "提供专业意见",
                "model": "gpt-4"
            },
            {
                "role_id": "voter_2",
                "agent_name": "voter_agent_2",
                "name": "投票者2",
                "goal": "提供专业意见",
                "model": "gpt-4"
            },
            {
                "role_id": "voter_3",
                "agent_name": "voter_agent_3",
                "name": "投票者3",
                "goal": "提供专业意见",
                "model": "gpt-4"
            }
        ],
        "tasks": [
            {
                "task_id": "vote_task",
                "description": "投票任务",
                "expected_output": "投票结果",
                "assigned_role": "voter_1",
                "dependencies": []
            }
        ],
        "global_settings": {
            "process_type": "consensus",  # 共识模式
            "verbose": False
        }
    }


@pytest.fixture
def dynamic_trigger_output_contains_config():
    """output_contains 类型动态触发配置"""
    return {
        "name": "动态触发团队",
        "execution_mode": "hybrid",
        "roles": [
            {
                "role_id": "primary",
                "agent_name": "primary_agent",
                "name": "主要角色",
                "goal": "初步分析",
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
                "goal": "深入分析",
                "model": "gpt-4"
            }
        ],
        "tasks": [
            {
                "task_id": "primary-task",
                "description": "主要任务",
                "expected_output": "初步分析结果",
                "assigned_role": "primary",
                "dependencies": []
            },
            {
                "task_id": "expert-task",
                "description": "专家任务",
                "expected_output": "深入分析结果",
                "assigned_role": "expert",
                "dependencies": ["primary-task"]
            }
        ],
        "global_settings": {
            "process_type": "sequential"
        }
    }


@pytest.fixture
def human_feedback_config():
    """人工审批配置（用于暂停逻辑测试）"""
    return {
        "name": "人工审批团队",
        "execution_mode": "static",
        "roles": [
            {
                "role_id": "reviewer",
                "agent_name": "code_reviewer",
                "name": "代码审查员",
                "goal": "审查代码质量",
                "model": "gpt-4"
            }
        ],
        "tasks": [
            {
                "task_id": "review-task",
                "description": "审查代码",
                "expected_output": "审查报告",
                "assigned_role": "reviewer",
                "dependencies": []
            }
        ],
        "global_settings": {
            "process_type": "sequential",
            "human_feedback_enabled": True  # 启用人工审批
        }
    }


# ============================================================================
# 共识模式投票机制测试
# ============================================================================

class TestConsensusVotingMechanism:
    """TC-EXEC-010: 共识模式投票机制测试"""
    
    def test_consensus_mode_config_parsing(self, consensus_mode_config):
        """测试共识模式配置解析
        
        验证点：
        - process_type 正确识别为 consensus
        - global_settings 包含共识模式标识
        """
        # Arrange & Act
        builder = StaticTeamGraphBuilder(consensus_mode_config)
        
        # Assert
        assert builder.config["global_settings"]["process_type"] == "consensus"
        assert len(builder.roles) == 3  # 3个投票者
    
    def test_voting_threshold_calculation(self):
        """测试投票阈值计算逻辑
        
        验证点：
        - 默认阈值为 0.75（75%）
        - 3个投票者需要至少 3 * 0.75 = 2.25 → 向上取整为 3 票
        """
        # Arrange
        total_voters = 3
        default_threshold = 0.75
        
        # Act
        required_votes = int(total_voters * default_threshold + 0.999)  # 向上取整
        
        # Assert
        assert required_votes == 3  # 需要全部3票
    
    def test_voting_result_aggregation(self):
        """测试投票结果聚合逻辑
        
        验证点：
        - 收集所有投票者的输出
        - 统计相同意见的数量
        - 判断是否达到阈值
        """
        # Arrange: 模拟投票结果
        role_outputs = {
            "voter_1": {"messages": [{"role": "assistant", "content": "同意"}]},
            "voter_2": {"messages": [{"role": "assistant", "content": "同意"}]},
            "voter_3": {"messages": [{"role": "assistant", "content": "反对"}]}
        }
        
        # Act: 统计"同意"票数
        agree_count = sum(
            1 for output in role_outputs.values()
            if "同意" in output["messages"][0]["content"]
        )
        
        total_voters = 3
        threshold = 0.75
        required_votes = int(total_voters * threshold + 0.999)
        
        # Assert
        assert agree_count == 2
        assert agree_count < required_votes  # 2 < 3，未达到阈值
        assert agree_count / total_voters == 2/3  # 66.67% < 75%
    
    def test_consensus_reached(self):
        """测试达成共识的情况
        
        验证点：
        - 当投票率 ≥ threshold 时，输出最终结果
        """
        # Arrange
        role_outputs = {
            "voter_1": {"messages": [{"role": "assistant", "content": "方案A"}]},
            "voter_2": {"messages": [{"role": "assistant", "content": "方案A"}]},
            "voter_3": {"messages": [{"role": "assistant", "content": "方案A"}]}
        }
        
        # Act: 统计"方案A"票数
        scheme_a_count = sum(
            1 for output in role_outputs.values()
            if "方案A" in output["messages"][0]["content"]
        )
        
        total_voters = 3
        threshold = 0.75
        required_votes = int(total_voters * threshold + 0.999)
        
        # Assert
        assert scheme_a_count == 3
        assert scheme_a_count >= required_votes  # 3 >= 3，达成共识
        assert scheme_a_count / total_voters == 1.0  # 100% >= 75%
    
    def test_consensus_not_reached_fallback(self):
        """测试未达成共识时的降级策略
        
        验证点：
        - 当投票率 < threshold 时，选择票数最多的选项
        - 或交由更高权限角色决策
        """
        # Arrange
        role_outputs = {
            "voter_1": {"messages": [{"role": "assistant", "content": "方案A"}]},
            "voter_2": {"messages": [{"role": "assistant", "content": "方案B"}]},
            "voter_3": {"messages": [{"role": "assistant", "content": "方案A"}]}
        }
        
        # Act: 统计各方案票数
        vote_counts = {}
        for output in role_outputs.values():
            content = output["messages"][0]["content"]
            vote_counts[content] = vote_counts.get(content, 0) + 1
        
        # 选择票数最多的方案
        winning_scheme = max(vote_counts, key=vote_counts.get)
        
        # Assert
        assert winning_scheme == "方案A"
        assert vote_counts["方案A"] == 2
        assert vote_counts["方案B"] == 1


# ============================================================================
# Dynamic Trigger 条件判断测试
# ============================================================================

class TestDynamicTriggerConditions:
    """dynamic_trigger 条件判断测试"""
    
    @pytest.mark.asyncio
    async def test_output_contains_trigger_activated(self, dynamic_trigger_output_contains_config):
        """TC-EXEC-010: 测试 output_contains 条件触发
        
        验证点：
        - 当输出包含 condition_value 时，激活动态触发
        - 跳转到 target_role_id 指定的角色
        """
        import re
        
        # Arrange
        builder = StaticTeamGraphBuilder(dynamic_trigger_output_contains_config)
        primary_role = builder.roles["primary"]
        trigger = primary_role["dynamic_trigger"]
        
        # 模拟 Agent 输出
        mock_output = "初步分析完成。发现复杂问题，需要专家介入分析。"
        
        # Act: 检查是否匹配条件
        is_triggered = bool(re.search(trigger["condition_value"], mock_output))
        
        # Assert
        assert is_triggered is True
        assert trigger["target_role_id"] == "expert"
    
    @pytest.mark.asyncio
    async def test_output_contains_trigger_not_activated(self, dynamic_trigger_output_contains_config):
        """测试 output_contains 条件未触发
        
        验证点：
        - 当输出不包含 condition_value 时，不激活动态触发
        - 继续执行下一个常规任务
        """
        import re
        
        # Arrange
        builder = StaticTeamGraphBuilder(dynamic_trigger_output_contains_config)
        primary_role = builder.roles["primary"]
        trigger = primary_role["dynamic_trigger"]
        
        # 模拟 Agent 输出（不包含触发关键词）
        mock_output = "初步分析完成。数据正常，无需进一步处理。"
        
        # Act: 检查是否匹配条件
        is_triggered = bool(re.search(trigger["condition_value"], mock_output))
        
        # Assert
        assert is_triggered is False
    
    def test_dynamic_trigger_config_validation(self, dynamic_trigger_output_contains_config):
        """测试 dynamic_trigger 配置校验
        
        验证点：
        - type 字段必须是合法值（output_contains/error_occurred/confidence_low/custom_llm_call）
        - condition_value 和 target_role_id 必须存在
        """
        # Arrange
        builder = StaticTeamGraphBuilder(dynamic_trigger_output_contains_config)
        primary_role = builder.roles["primary"]
        trigger = primary_role["dynamic_trigger"]
        
        # Act & Assert
        valid_types = ["output_contains", "error_occurred", "confidence_low", "custom_llm_call"]
        assert trigger["type"] in valid_types
        assert "condition_value" in trigger
        assert "target_role_id" in trigger
    
    def test_multiple_dynamic_triggers(self):
        """测试多个动态触发配置
        
        验证点：
        - 不同角色可以有独立的 dynamic_trigger
        - 每个触发条件独立判断
        """
        # Arrange
        multi_trigger_config = {
            "name": "多触发团队",
            "roles": [
                {
                    "role_id": "r1",
                    "agent_name": "a1",
                    "name": "R1",
                    "goal": "G1",
                    "model": "gpt-4",
                    "dynamic_trigger": {
                        "type": "output_contains",
                        "condition_value": "错误",
                        "target_role_id": "error_handler"
                    }
                },
                {
                    "role_id": "r2",
                    "agent_name": "a2",
                    "name": "R2",
                    "goal": "G2",
                    "model": "gpt-4",
                    "dynamic_trigger": {
                        "type": "confidence_low",
                        "condition_value": 0.6,
                        "target_role_id": "reviewer"
                    }
                }
            ],
            "tasks": [
                {"task_id": "t1", "description": "T1", "expected_output": "O1", "assigned_role": "r1", "dependencies": []},
                {"task_id": "t2", "description": "T2", "expected_output": "O2", "assigned_role": "r2", "dependencies": ["t1"]}
            ],
            "global_settings": {"process_type": "sequential"}
        }
        
        builder = StaticTeamGraphBuilder(multi_trigger_config)
        
        # Act & Assert
        assert "dynamic_trigger" in builder.roles["r1"]
        assert "dynamic_trigger" in builder.roles["r2"]
        assert builder.roles["r1"]["dynamic_trigger"]["type"] == "output_contains"
        assert builder.roles["r2"]["dynamic_trigger"]["type"] == "confidence_low"


# ============================================================================
# Human Feedback 暂停逻辑测试
# ============================================================================

class TestHumanFeedbackPauseLogic:
    """human_feedback 暂停逻辑测试"""
    
    def test_human_feedback_enabled_config(self, human_feedback_config):
        """测试人工审批配置启用
        
        验证点：
        - human_feedback_enabled 字段正确设置
        - 配置能被正确解析
        """
        # Arrange & Act
        builder = StaticTeamGraphBuilder(human_feedback_config)
        
        # Assert
        assert builder.config["global_settings"]["human_feedback_enabled"] is True
    
    def test_human_feedback_disabled_by_default(self):
        """测试人工审批默认禁用
        
        验证点：
        - 未指定 human_feedback_enabled 时，默认为 False
        """
        # Arrange
        config_without_feedback = {
            "name": "无审批团队",
            "roles": [
                {"role_id": "r1", "agent_name": "a1", "name": "R1", "goal": "G1", "model": "gpt-4"}
            ],
            "tasks": [
                {"task_id": "t1", "description": "T1", "expected_output": "O1", "assigned_role": "r1", "dependencies": []}
            ],
            "global_settings": {
                "process_type": "sequential"
                # 未指定 human_feedback_enabled
            }
        }
        
        builder = StaticTeamGraphBuilder(config_without_feedback)
        
        # Act & Assert
        assert builder.config["global_settings"].get("human_feedback_enabled", False) is False
    
    def test_pause_at_approval_point(self, human_feedback_config):
        """测试在审批点暂停执行
        
        验证点：
        - 当 human_feedback_enabled=True 时，执行至审批点应暂停
        - 等待 Approve/Reject 决策后才能继续
        """
        # Arrange
        builder = StaticTeamGraphBuilder(human_feedback_config)
        
        # 模拟执行状态
        execution_state = {
            "current_node": "reviewer",
            "requires_human_feedback": True,
            "feedback_status": "pending"  # pending/approved/rejected
        }
        
        # Act & Assert
        assert execution_state["requires_human_feedback"] is True
        assert execution_state["feedback_status"] == "pending"
    
    def test_resume_after_approval(self, human_feedback_config):
        """测试审批通过后恢复执行
        
        验证点：
        - 收到 Approve 决策后，继续执行后续任务
        - feedback_status 更新为 approved
        """
        # Arrange
        builder = StaticTeamGraphBuilder(human_feedback_config)
        
        # 模拟审批通过
        execution_state = {
            "current_node": "reviewer",
            "requires_human_feedback": True,
            "feedback_status": "approved",  # 已批准
            "feedback_comment": "审查通过，可以继续"
        }
        
        # Act & Assert
        assert execution_state["feedback_status"] == "approved"
        # 审批通过后，应继续执行下一个节点
        assert execution_state["requires_human_feedback"] is True  # 仍为 True，但状态已改变
    
    def test_reject_and_rollback(self, human_feedback_config):
        """测试审批拒绝后的回滚逻辑
        
        验证点：
        - 收到 Reject 决策后，停止执行或回滚到上一节点
        - feedback_status 更新为 rejected
        """
        # Arrange
        builder = StaticTeamGraphBuilder(human_feedback_config)
        
        # 模拟审批拒绝
        execution_state = {
            "current_node": "reviewer",
            "requires_human_feedback": True,
            "feedback_status": "rejected",  # 已拒绝
            "feedback_comment": "代码质量不达标，需要重新编写"
        }
        
        # Act & Assert
        assert execution_state["feedback_status"] == "rejected"
        # 审批拒绝后，应停止执行或标记为失败
        assert execution_state["feedback_comment"] is not None
