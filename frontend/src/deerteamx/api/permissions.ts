/**
 * DeerTeamX API 客户端 - Permissions
 * 对齐 @/core/api 风格,严格遵循后端接口定义
 */

import type { PermissionResponse, RoleUpdateRequest, RoleUpdateResponse } from '../types';

const DEERTEAMX_BASE_URL =
  process.env.NEXT_PUBLIC_DEERTEAMX_API_URL || 'http://localhost:8000';

/**
 * 获取认证Token
 */
function getAuthToken(): string {
  return typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
}

/**
 * 获取权限矩阵
 */
export async function getPermissions(): Promise<PermissionResponse> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/permissions`, {
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get permissions: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 切换角色
 */
export async function updateRole(data: RoleUpdateRequest): Promise<RoleUpdateResponse> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/users/me/role`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getAuthToken()}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update role: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}
