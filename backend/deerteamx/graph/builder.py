"""DeerTeamX 静态团队图构建器。

该模块负责将 DeerTeamX 的团队配置（角色、任务、依赖关系）转换为
LangGraph StateGraph，并复用 DeerFlow 的 Agent 工厂进行节点执行。
"""

import logging
import re
from typing import Any, Dict, List, Optional, TypedDict

import httpx
from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnableConfig

# 导入 DeerFlow 核心组件（通过 Submodule 或 pip 安装）
try:
    from deerflow.agents.lead_agent.agent import make_lead_agent
    from deerflow.config.paths import get_paths
except ImportError:
    raise ImportError("请确保已正确配置 DeerFlow Submodule 或安装了 deerflow 包")

logger = logging.getLogger(__name__)


class TeamState(TypedDict):
    """LangGraph 状态定义。"""
    messages: list  # 消息历史
    current_role: str  # 当前执行的角色 ID
    role_outputs: dict  # 各角色输出结果 {role_id: output}
    execution_order: list  # 实际执行顺序记录
    __next_node__: Optional[str]  # 用于动态触发跳转的下一个节点标识


class StaticTeamGraphBuilder:
    """将 DeerTeamX 团队配置转换为 LangGraph StateGraph。"""

    def __init__(self, team_config: dict, gateway_url: str = "http://localhost:8001"):
        self.config = team_config
        self.roles = {r["role_id"]: r for r in team_config.get("roles", [])}
        self.tasks = team_config.get("tasks", [])
        self.gateway_url = gateway_url

    def build(self) -> Any:
        """构建并编译完整的 StateGraph。"""
        workflow = StateGraph(TeamState)

        # 1. 注册角色节点
        for role_id, role in self.roles.items():
            node_func = self._create_agent_node(role_id, role)
            workflow.add_node(role_id, node_func)

        # 2. 构建 DAG 边与条件边
        self._add_edges(workflow)

        # 3. 设置入口点
        entry_task = self._find_entry_task()
        if entry_task:
            workflow.set_entry_point(entry_task)

        return workflow.compile()

    def _create_agent_node(self, role_id: str, role: dict):
        """创建角色节点函数，内部调用 DeerFlow 的 make_lead_agent。"""
        agent_name = role.get("agent_name") or role_id
        
        async def agent_node(state: TeamState) -> Dict[str, Any]:
            logger.info(f"Executing role node: {role_id}")
            
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

            # 准备输入上下文
            context = self._build_role_context(role, state)
            input_messages = state.get("messages", [])
            if context:
                input_messages.append({"role": "user", "content": context})

            # 执行 Agent
            result = await agent_executor.ainvoke({"messages": input_messages})

            # 处理 Dynamic Trigger 逻辑
            next_node = None
            trigger = role.get("dynamic_trigger")
            if trigger and trigger.get("type") == "output_contains":
                last_msg = result["messages"][-1] if result.get("messages") else None
                if last_msg and re.search(trigger["condition_value"], last_msg.content):
                    next_node = trigger.get("target_role_id")
                    logger.info(f"Dynamic trigger activated: {role_id} -> {next_node}")

            return {
                "messages": result["messages"],
                "current_role": role_id,
                "role_outputs": {**state.get("role_outputs", {}), role_id: result},
                "execution_order": state.get("execution_order", []) + [role_id],
                "__next_node__": next_node,
            }

        return agent_node

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

    def _build_role_context(self, role: dict, state: TeamState) -> str:
        """构建包含前置任务输出的角色上下文。"""
        parts = [f"## 你的角色\n- **名称**: {role.get('name')}\n- **目标**: {role.get('goal')}"]
        
        # 查找依赖于当前角色的任务输出
        deps = [t["task_id"] for t in self.tasks if role["role_id"] in t.get("dependencies", [])]
        for dep_id in deps:
            if dep_id in state.get("role_outputs", {}):
                output = state["role_outputs"][dep_id]
                content = output["messages"][-1].content if output.get("messages") else ""
                parts.append(f"\n## 前置任务 [{dep_id}] 的输出\n{content}")
        
        return "\n".join(parts)

    def _add_edges(self, workflow: StateGraph):
        """添加基础依赖边和动态触发条件边。"""
        task_map = {t["task_id"]: t for t in self.tasks}
        
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
                    lambda state: state.get("__next_node__") or END,
                    {**{r["role_id"]: r["role_id"] for r in self.roles.values()}, END: END}
                )
            elif not any(task_id in t.get("dependencies", []) for t in self.tasks):
                # 如果没有后继且不是动态触发，直接连到 END
                workflow.add_edge(task_id, END)

    def _find_entry_task(self) -> Optional[str]:
        """找到入口任务（没有任何依赖的任务）。"""
        all_ids = {t["task_id"] for t in self.tasks}
        all_deps = {d for t in self.tasks for d in t.get("dependencies", [])}
        entries = all_ids - all_deps
        return entries.pop() if entries else None
