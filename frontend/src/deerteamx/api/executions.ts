/**
 * DeerTeamX API 客户端 - Executions
 * 对齐 @/core/api 风格,严格遵循后端接口定义
 */

import type {
  Execution,
  ExecutionListResponse,
  ExecutionListParams,
  TriggerExecutionRequest,
  TriggerExecutionResponse,
} from '../types';

const DEERTEAMX_BASE_URL =
  process.env.NEXT_PUBLIC_DEERTEAMX_API_URL || 'http://localhost:8000';

/**
 * 获取认证Token
 */
function getAuthToken(): string {
  return typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
}

/**
 * 触发执行
 */
export async function triggerExecution(
  data: TriggerExecutionRequest
): Promise<TriggerExecutionResponse> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/executions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getAuthToken()}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger execution: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 查询执行状态
 */
export async function getExecution(executionId: string): Promise<Execution> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/executions/${executionId}`, {
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get execution: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 列出执行历史
 */
export async function listExecutions(params?: ExecutionListParams): Promise<ExecutionListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.team_id) queryParams.set('team_id', params.team_id);
  if (params?.status) queryParams.set('status', params.status);
  if (params?.limit) queryParams.set('limit', String(params.limit));
  if (params?.offset) queryParams.set('offset', String(params.offset));

  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/executions?${queryParams}`, {
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to list executions: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}
