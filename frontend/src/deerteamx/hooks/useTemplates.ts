/**
 * DeerTeamX Hooks - Templates
 * 基于 TanStack Query v5
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTemplates, saveAsTemplate, useTemplate } from '../api/templates';
import { TEMPLATE_KEYS } from './query-keys';
import type { SaveAsTemplateRequest, UseTemplateRequest } from '../types';

/**
 * 获取模板列表
 */
export function useTemplates(filters?: { scope?: 'system' | 'personal' | 'all'; keyword?: string }) {
  return useQuery({
    queryKey: TEMPLATE_KEYS.list({
      scope: filters?.scope,
      keyword: filters?.keyword,
    }),
    queryFn: () =>
      listTemplates({
        scope: filters?.scope,
        keyword: filters?.keyword,
      }),
  });
}

/**
 * 保存为模板
 */
export function useSaveAsTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SaveAsTemplateRequest) => saveAsTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TEMPLATE_KEYS.lists() });
    },
  });
}

/**
 * 使用模板创建团队
 */
export function useUseTemplate(templateId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UseTemplateRequest) => useTemplate(templateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deerteamx', 'teams'] });
    },
  });
}
