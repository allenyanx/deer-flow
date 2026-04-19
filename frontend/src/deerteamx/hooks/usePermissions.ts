/**
 * DeerTeamX Hooks - Permissions
 * 基于 TanStack Query v5
 */

'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { getPermissions, updateRole } from '../api/permissions';
import { PERMISSION_KEYS } from './query-keys';
import type { RoleUpdateRequest } from '../types';

/**
 * 获取权限矩阵
 */
export function usePermissions() {
  return useQuery({
    queryKey: PERMISSION_KEYS.current(),
    queryFn: () => getPermissions(),
  });
}

/**
 * 切换角色
 */
export function useUpdateRole() {
  return useMutation({
    mutationFn: (data: RoleUpdateRequest) => updateRole(data),
  });
}

/**
 * 权限检查 Hook
 * 基于权限矩阵控制组件显隐
 */
export function usePermission() {
  const { data } = usePermissions();

  const can = (resource: string, action: string): boolean => {
    if (!data?.permissions) return false;
    return (data.permissions as any)[resource]?.[action] ?? false;
  };

  return { can, roleType: data?.role_type };
}
