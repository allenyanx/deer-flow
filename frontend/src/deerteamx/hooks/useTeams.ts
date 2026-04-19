/**
 * DeerTeamX Hooks - Teams
 * 基于 TanStack Query v5,对齐 @/hooks 风格
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listTeams,
  getTeam,
  createTeam,
  updateTeam,
  deleteTeam,
  checkTeamName,
} from '../api/teams';
import { TEAM_KEYS } from './query-keys';
import type { CreateTeamRequest, UpdateTeamRequest } from '../types';

/**
 * 获取团队列表
 */
export function useTeams(filters?: {
  page?: number;
  page_size?: number;
  status?: string;
  keyword?: string;
}) {
  return useQuery({
    queryKey: TEAM_KEYS.list({
      page: filters?.page,
      page_size: filters?.page_size,
      status: filters?.status,
      keyword: filters?.keyword,
    }),
    queryFn: () =>
      listTeams({
        page: filters?.page,
        page_size: filters?.page_size,
        status: filters?.status,
        keyword: filters?.keyword,
      }),
  });
}

/**
 * 获取团队详情
 */
export function useTeam(teamId: string) {
  return useQuery({
    queryKey: TEAM_KEYS.detail(teamId),
    queryFn: () => getTeam(teamId),
    enabled: !!teamId,
  });
}

/**
 * 创建团队
 */
export function useCreateTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateTeamRequest) => createTeam(data),
    onSuccess: () => {
      // 失效团队列表缓存
      queryClient.invalidateQueries({ queryKey: TEAM_KEYS.lists() });
    },
  });
}

/**
 * 更新团队
 */
export function useUpdateTeam(teamId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateTeamRequest) => updateTeam(teamId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TEAM_KEYS.detail(teamId) });
      queryClient.invalidateQueries({ queryKey: TEAM_KEYS.lists() });
    },
  });
}

/**
 * 删除团队
 */
export function useDeleteTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (teamId: string) => deleteTeam(teamId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TEAM_KEYS.lists() });
    },
  });
}

/**
 * 检查团队名称可用性
 */
export function useCheckTeamName() {
  return useMutation({
    mutationFn: (name: string) => checkTeamName(name),
  });
}
