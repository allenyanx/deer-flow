/**
 * DeerTeamX API 客户端 - Teams
 * 对齐 @/core/api 风格,严格遵循后端接口定义
 */

import type {
  Team,
  TeamSummary,
  TeamListResponse,
  CreateTeamRequest,
  UpdateTeamRequest,
  NameAvailabilityResponse,
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
 * 创建团队
 */
export async function createTeam(data: CreateTeamRequest): Promise<Team> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/teams`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getAuthToken()}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create team: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 列出团队
 */
export async function listTeams(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  keyword?: string;
  sort_by?: string;
  sort_order?: string;
}): Promise<TeamListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.page) queryParams.set('page', String(params.page));
  if (params?.page_size) queryParams.set('page_size', String(params.page_size));
  if (params?.status) queryParams.set('status', params.status);
  if (params?.keyword) queryParams.set('keyword', params.keyword);
  if (params?.sort_by) queryParams.set('sort_by', params.sort_by);
  if (params?.sort_order) queryParams.set('sort_order', params.sort_order);

  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/teams?${queryParams}`, {
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to list teams: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 获取团队详情
 */
export async function getTeam(teamId: string): Promise<Team> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/teams/${teamId}`, {
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get team: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 更新团队
 */
export async function updateTeam(teamId: string, data: UpdateTeamRequest): Promise<Team> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/teams/${teamId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getAuthToken()}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update team: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 删除团队
 */
export async function deleteTeam(teamId: string): Promise<void> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/teams/${teamId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to delete team: ${response.statusText}`);
  }
}

/**
 * 检查团队名称可用性
 */
export async function checkTeamName(name: string): Promise<NameAvailabilityResponse> {
  const response = await fetch(
    `${DEERTEAMX_BASE_URL}/api/v1/teams/check-name?name=${encodeURIComponent(name)}`,
    {
      headers: {
        Authorization: `Bearer ${getAuthToken()}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to check name: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}
