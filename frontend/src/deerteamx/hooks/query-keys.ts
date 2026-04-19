/**
 * DeerTeamX Query Keys - TanStack Query 命名空间隔离
 * 所有 Key 以 'deerteamx' 为前缀,避免与 DeerFlow 现有 keys 冲突
 */

export const TEAM_KEYS = {
  all: ['deerteamx', 'teams'] as const,
  lists: () => [...TEAM_KEYS.all, 'list'] as const,
  list: (filters: { page?: number; page_size?: number; status?: string; keyword?: string }) =>
    [...TEAM_KEYS.lists(), filters] as const,
  details: () => [...TEAM_KEYS.all, 'detail'] as const,
  detail: (teamId: string) => [...TEAM_KEYS.details(), teamId] as const,
};

export const EXECUTION_KEYS = {
  all: ['deerteamx', 'executions'] as const,
  lists: () => [...EXECUTION_KEYS.all, 'list'] as const,
  list: (filters: { team_id?: string; status?: string; limit?: number; offset?: number }) =>
    [...EXECUTION_KEYS.lists(), filters] as const,
  details: () => [...EXECUTION_KEYS.all, 'detail'] as const,
  detail: (executionId: string) => [...EXECUTION_KEYS.details(), executionId] as const,
};

export const TEMPLATE_KEYS = {
  all: ['deerteamx', 'templates'] as const,
  lists: () => [...TEMPLATE_KEYS.all, 'list'] as const,
  list: (filters: { scope?: string; keyword?: string }) =>
    [...TEMPLATE_KEYS.lists(), filters] as const,
};

export const PERMISSION_KEYS = {
  all: ['deerteamx', 'permissions'] as const,
  current: () => [...PERMISSION_KEYS.all, 'current'] as const,
};
