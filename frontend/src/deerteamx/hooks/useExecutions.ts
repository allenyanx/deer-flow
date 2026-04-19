/**
 * DeerTeamX Hooks - Executions
 * 基于 TanStack Query v5
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { triggerExecution, getExecution, listExecutions } from '../api/executions';
import { EXECUTION_KEYS } from './query-keys';
import type { TriggerExecutionRequest, ExecutionListParams } from '../types';

/**
 * 触发执行
 */
export function useTriggerExecution() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TriggerExecutionRequest) => triggerExecution(data),
    onSuccess: () => {
      // 失效执行列表缓存
      queryClient.invalidateQueries({ queryKey: EXECUTION_KEYS.lists() });
    },
  });
}

/**
 * 获取执行详情
 */
export function useExecution(executionId: string) {
  return useQuery({
    queryKey: EXECUTION_KEYS.detail(executionId),
    queryFn: () => getExecution(executionId),
    enabled: !!executionId,
  });
}

/**
 * 获取执行历史列表
 */
export function useExecutions(params?: ExecutionListParams) {
  return useQuery({
    queryKey: EXECUTION_KEYS.list(params || {}),
    queryFn: () => listExecutions(params),
  });
}
