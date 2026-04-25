"""DeerTeamX 静态团队图构建器。

该模块负责将 DeerTeamX 的团队配置（角色、任务、依赖关系）转换为
LangGraph StateGraph，并复用 DeerFlow 的 Agent 工厂进行节点执行。
"""

import logging
import re
import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

import httpx
from langgraph.graph import END, StateGraph, add_messages
from langchain_core.runnables import RunnableConfig

# 导入 DeerFlow 核心组件（通过 Submodule 或 pip 安装）
try:
    from deerflow.agents.lead_agent.agent import make_lead_agent
    from deerflow.config.paths import get_paths
except ImportError:
    raise ImportError("请确保已正确配置 DeerFlow Submodule 或安装了 deerflow 包")

logger = logging.getLogger(__name__)


def merge_dicts(d1: dict, d2: dict) -> dict:
    """合并两个字典，用于并行任务输出的累加。"""
    return {**d1, **d2}

def merge_lists(l1: list, l2: list) -> list:
    """合并两个列表，用于记录已完成的任务序列。"""
    return l1 + l2

class TeamState(TypedDict):
    """LangGraph 状态定义（方案 A：支持并行安全）。"""
    messages: Annotated[list, add_messages]  # 消息历史（自动追加）
    current_task: str  # 当前执行的任务 ID
    task_outputs: Annotated[dict, merge_dicts]  # 各任务输出结果 {task_id: output}
    completed_tasks: Annotated[list, merge_lists]  # 已完成的任务列表
    __next_node__: Optional[str]  # 用于动态触发跳转的下一个节点标识


class StaticTeamGraphBuilder:
    """将 DeerTeamX 团队配置转换为 LangGraph StateGraph。"""

    def __init__(self, team_config: dict, gateway_url: str = "http://localhost:8001"):
        self.config = team_config
        self.roles = {r["role_id"]: r for r in team_config.get("roles", [])}
        self.tasks = team_config.get("tasks", [])
        self.gateway_url = gateway_url

    def build(self) -> Any:
        """构建并编译完整的 StateGraph（方案 A：以 Task 为节点）。"""
        workflow = StateGraph(TeamState)

        # 1. 注册任务节点（每个任务对应一个节点）
        for task in self.tasks:
            node_func = self._create_task_node(task)
            workflow.add_node(task["task_id"], node_func)

        # 2. 构建 DAG 边与条件边
        self._add_edges(workflow)

        # 3. 设置入口点（支持多个并行入口）
        entry_tasks = self._find_entry_tasks()
        for entry_task_id in entry_tasks:
            workflow.add_edge("__start__", entry_task_id)

        return workflow.compile()

    def _create_task_node(self, task: dict):
        """创建任务节点函数，内部根据 assigned_role 调用对应的 Agent。"""
        task_id = task["task_id"]
        assigned_role_id = task.get("assigned_role")
        
        if not assigned_role_id or assigned_role_id not in self.roles:
            raise ValueError(f"Task {task_id} has invalid assigned_role: {assigned_role_id}")
        
        role = self.roles[assigned_role_id]
        agent_name = role.get("agent_name") or assigned_role_id
        
        async def task_node(state: TeamState) -> Dict[str, Any]:
            logger.info(f"Executing task node: {task_id} (role: {assigned_role_id})")
            
            # 确保 Custom Agent 存在并已绑定 Skills
            await self._ensure_custom_agent_exists(agent_name, role)

            # 构造 RunnableConfig
            config = RunnableConfig(
                configurable={
                    "agent_name": agent_name,
                    "model_name": role.get("model"),
                    "thinking_enabled": role.get("thinking_enabled", True),
                    "subagent_enabled": role.get("subagent_enabled", False),
                    "max_concurrent_subagents": role.get("max_concurrent_subagents", 3),
                }
            )

            # 调用 DeerFlow Agent 工厂
            agent_executor = make_lead_agent(config)

            # 准备输入上下文（包含前置任务的输出）
            context = self._build_task_context(task, state)
            input_messages = state.get("messages", [])
            if context:
                input_messages.append({"role": "user", "content": context})

            # 执行 Agent
            result = await agent_executor.ainvoke({"messages": input_messages})

            # 处理 Dynamic Trigger 逻辑
            next_node = None
            trigger = task.get("dynamic_trigger")
            if trigger and trigger.get("type") == "output_contains":
                last_msg = result["messages"][-1] if result.get("messages") else None
                if last_msg and re.search(trigger["condition_value"], last_msg.content):
                    next_node = trigger.get("target_task_id")
                    logger.info(f"Dynamic trigger activated: {task_id} -> {next_node}")

            return {
                "messages": result["messages"],
                "current_task": task_id,
                "task_outputs": {**state.get("task_outputs", {}), task_id: result},
                "completed_tasks": state.get("completed_tasks", []) + [task_id],
                "__next_node__": next_node,
            }

        return task_node

    async def _ensure_custom_agent_exists(self, agent_name: str, role: dict):
        """确保 Custom Agent 存在，并通过 API 原子性更新 Skills。"""
        async with httpx.AsyncClient() as client:
            # 1. 检查是否存在
            resp = await client.get(f"{self.gateway_url}/api/agents/{agent_name}")
            
            if resp.status_code == 404:
                # 2. 不存在则创建
                create_resp = await client.post(
                    f"{self.gateway_url}/api/agents",
                    json={
                        "name": agent_name,
                        "description": role.get("description", ""),
                        "model": role.get("model"),
                        "tool_groups": role.get("tool_groups"),
                        "soul": role.get("soul_content", "")
                    }
                )
                if create_resp.status_code not in [201, 409]:
                    raise Exception(f"Failed to create agent {agent_name}: {create_resp.text}")

            # 3. 原子性更新 Skills (方案 A)
            skills = role.get("skills", [])
            skills_resp = await client.put(
                f"{self.gateway_url}/api/agents/{agent_name}/skills",
                json={"skills": skills}
            )
            if skills_resp.status_code != 200:
                logger.warning(f"Failed to update skills for {agent_name}: {skills_resp.text}")

    def _build_task_context(self, task: dict, state: TeamState) -> str:
        """构建包含前置任务输出的任务上下文。"""
        parts = []
        role = self.roles[task["assigned_role"]]
        
        # 添加当前角色的基础信息
        parts.append(f"## 你的角色\n- **名称**: {role.get('name')}\n- **目标**: {role.get('goal')}")
        
        # 添加前置依赖任务的输出
        dependencies = task.get("dependencies", [])
        for dep_id in dependencies:
            if dep_id in state.get("task_outputs", {}):
                output = state["task_outputs"][dep_id]
                content = output["messages"][-1].content if output.get("messages") else ""
                parts.append(f"\n## 前置任务 [{dep_id}] 的输出\n{content}")
        
        # 添加当前任务的描述
        parts.append(f"\n## 当前任务 [{task['task_id']}]\n- **描述**: {task.get('description')}\n- **预期输出**: {task.get('expected_output')}")
        
        return "\n".join(parts)

    def _add_edges(self, workflow: StateGraph):
        """添加基础依赖边和动态触发条件边（基于 Task ID）。"""
        for task in self.tasks:
            task_id = task["task_id"]
            dependencies = task.get("dependencies", [])
            
            # 添加基础依赖边
            for dep_id in dependencies:
                workflow.add_edge(dep_id, task_id)
            
            # 处理动态触发条件边
            if task.get("dynamic_trigger"):
                workflow.add_conditional_edges(
                    task_id,
                    lambda state, tid=task_id: state.get("__next_node__") if state.get("current_task") == tid else END,
                    {t["task_id"]: t["task_id"] for t in self.tasks} | {END: END}
                )
            elif not any(task_id in t.get("dependencies", []) for t in self.tasks):
                # 如果没有后继且不是动态触发，直接连到 END
                workflow.add_edge(task_id, END)

    def _find_entry_tasks(self) -> List[str]:
        """找到所有入口任务（没有任何依赖的任务）。"""
        entry_tasks = []
        for task in self.tasks:
            if not task.get("dependencies", []):
                entry_tasks.append(task["task_id"])
        return entry_tasks
