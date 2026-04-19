/**
 * DeerTeamX 类型定义 - 团队相关
 * 严格对齐后端 API_REFERENCE.md 第3节
 */

/**
 * 执行模式枚举
 */
export type ExecutionMode = 'static' | 'hybrid';

/**
 * 团队状态枚举
 */
export type TeamStatus = 'draft' | 'executing' | 'completed' | 'failed';

/**
 * 流程类型枚举
 */
export type ProcessType = 'sequential' | 'hierarchical' | 'consensus';

/**
 * 动态触发器类型
 */
export interface DynamicTrigger {
  type: 'output_contains' | 'error_occurred' | 'confidence_low' | 'custom_llm_call';
  condition_value: string | string[] | number;
  dynamic_agent_name: string;
}

/**
 * 角色配置
 */
export interface Role {
  role_id: string;
  agent_name: string;
  name: string;
  goal: string;
  backstory?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  tool_groups?: string[];
  skills?: string[];
  memory_enabled?: boolean;
  verbose?: boolean;
  allow_delegation?: boolean;
  max_iter?: number;
  max_retry_limit?: number;
}

/**
 * 任务配置
 */
export interface Task {
  task_id: string;
  description: string;
  expected_output: string;
  assigned_role: string; // 对应 role_id
  dependencies: string[]; // 前置任务 task_id 列表
  dynamic_trigger?: DynamicTrigger;
}

/**
 * 全局设置
 */
export interface GlobalSettings {
  process_type: ProcessType;
  verbose?: boolean;
  manager_llm_model?: string;
  manager_agent_id?: string;
  crew_memory_enabled?: boolean;
  max_rpm?: number;
  cache_enabled?: boolean;
  long_term_memory_enabled?: boolean;
  share_crew?: boolean;
  state_persistence?: boolean;
  human_feedback_enabled?: boolean;
}

/**
 * 团队完整配置
 */
export interface Team {
  team_id: string;
  name: string;
  description?: string;
  execution_mode: ExecutionMode;
  version: string; // 语义化版本 vX.Y.Z
  status: TeamStatus;
  roles: Role[];
  tasks: Task[];
  global_settings: GlobalSettings;
  creator_id: string;
  created_at: string; // ISO 8601 格式
  updated_at: string;
}

/**
 * 创建团队请求
 */
export interface CreateTeamRequest {
  name: string;
  description?: string;
  execution_mode: ExecutionMode;
  roles: Omit<Role, 'role_id'>[];
  tasks: Omit<Task, 'task_id'>[];
  global_settings: GlobalSettings;
}

/**
 * 更新团队请求
 */
export interface UpdateTeamRequest extends Partial<CreateTeamRequest> {
  version?: string; // 乐观锁版本号
}

/**
 * 团队摘要信息（列表展示用）
 */
export interface TeamSummary {
  team_id: string;
  name: string;
  execution_mode: ExecutionMode;
  status: TeamStatus;
  creator_name: string;
  create_time: string;
  update_time: string;
  latest_execution?: {
    execution_id: string;
    status: string;
    token_stats: {
      total_input_tokens: number;
      total_output_tokens: number;
      total_cost_cents: number;
    };
  };
}

/**
 * 团队列表响应
 */
export interface TeamListResponse {
  teams: TeamSummary[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

/**
 * 名称可用性检查响应
 */
export interface NameAvailabilityResponse {
  available: boolean;
  suggested_name?: string;
}
