/**
 * DeerTeamX 权限守卫组件
 * 基于 usePermission Hook 控制组件显隐
 * 对齐权限系统实现方案 8.8.5 节
 */

'use client';

import { ReactNode } from 'react';
import { usePermission } from '../../hooks/usePermissions';

interface PermissionGuardProps {
  resource: string;
  action: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function PermissionGuard({
  resource,
  action,
  children,
  fallback = null,
}: PermissionGuardProps) {
  const { can } = usePermission();

  return can(resource, action) ? <>{children}</> : <>{fallback}</>;
}
