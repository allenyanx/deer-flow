/**
 * DeerTeamX 类型定义 - 执行相关
 * 严格对齐后端 API_REFERENCE.md 第4节
 */

/**
 * 执行状态枚举
 */
export type ExecutionStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'waiting_approval'
  | 'approval_timeout'
  | 'approval_rejected';

/**
 * Token统计
 */
export interface TokenStats {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_cents: number;
}

/**
 * 执行进度
 */
export interface ExecutionProgress {
  current_node: string;
  completed_nodes: string[];
  total_nodes: number;
}

/**
 * 执行详情
 */
export interface Execution {
  execution_id: string;
  team_id: string;
  thread_id: string;
  status: ExecutionStatus;
  progress?: ExecutionProgress;
  input_data: Record<string, any>;
  output_data?: any;
  execution_order: string[];
  token_stats?: TokenStats;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

/**
 * 触发执行请求
 */
export interface TriggerExecutionRequest {
  team_id: string;
  input_data: Record<string, any>;
}

/**
 * 触发执行响应
 */
export interface TriggerExecutionResponse {
  execution_id: string;
  status: ExecutionStatus;
  created_at: string;
}

/**
 * 执行列表查询参数
 */
export interface ExecutionListParams {
  team_id?: string;
  status?: ExecutionStatus;
  limit?: number;
  offset?: number;
}

/**
 * 执行列表响应
 */
export interface ExecutionListResponse {
  executions: Execution[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
  };
}

/**
 * WebSocket 消息基础结构
 */
export interface WSMessage {
  type: 'execution_update' | 'execution_completed' | 'error';
  execution_id: string;
  thread_id: string;
  timestamp: string;
  payload: {
    event_type: string;
    data: any;
    metadata?: {
      node_name?: string;
      run_id?: string;
    };
  };
}
