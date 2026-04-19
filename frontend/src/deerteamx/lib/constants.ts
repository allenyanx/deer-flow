/**
 * DeerTeamX 常量定义
 */

// 权限码枚举
export const PermissionCodes = {
  // 团队操作
  TEAM_LIST: 'team:list',
  TEAM_CREATE: 'team:create',
  TEAM_EDIT: 'team:edit',
  TEAM_DELETE: 'team:delete',
  TEAM_EXECUTE: 'team:execute',
  TEAM_IMPORT: 'team:import',

  // 模板操作
  TEMPLATE_LIST: 'template:list',
  TEMPLATE_USE: 'template:use',
  TEMPLATE_CREATE: 'template:create',
  TEMPLATE_EDIT: 'template:edit',
  TEMPLATE_DELETE: 'template:delete',

  // 导出
  EXPORT_RESULT: 'export:result',
} as const;

// 角色类型枚举
export const RoleTypes = {
  DEVELOPER: 'developer',
  RESEARCHER: 'researcher',
  ENTHUSIAST: 'enthusiast',
} as const;

// 执行状态枚举
export const ExecutionStatuses = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
  WAITING_APPROVAL: 'waiting_approval',
  APPROVAL_TIMEOUT: 'approval_timeout',
  APPROVAL_REJECTED: 'approval_rejected',
} as const;
