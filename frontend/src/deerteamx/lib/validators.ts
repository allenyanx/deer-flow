/**
 * DeerTeamX Zod Schema 校验器
 * 用于表单参数校验
 */

import { z } from 'zod';

/**
 * 创建团队请求校验 Schema
 */
export const CreateTeamSchema = z.object({
  name: z.string().min(1, '团队名称不能为空').max(100, '团队名称不能超过100字符'),
  description: z.string().max(500, '描述不能超过500字符').optional(),
  execution_mode: z.enum(['static', 'hybrid']),
  roles: z.array(
    z.object({
      agent_name: z.string().min(1, 'Agent名称不能为空'),
      name: z.string().min(1, '角色名称不能为空'),
      goal: z.string().min(1, '目标不能为空'),
      backstory: z.string().optional(),
      model: z.string().optional(),
      temperature: z.number().min(0).max(2).optional(),
      max_tokens: z.number().int().positive().optional(),
      tool_groups: z.array(z.string()).optional(),
      skills: z.array(z.string()).optional(),
      memory_enabled: z.boolean().optional(),
      verbose: z.boolean().optional(),
      allow_delegation: z.boolean().optional(),
      max_iter: z.number().int().positive().optional(),
      max_retry_limit: z.number().int().nonnegative().optional(),
    })
  ).min(1, '至少需要一个角色'),
  tasks: z.array(
    z.object({
      description: z.string().min(1, '任务描述不能为空'),
      expected_output: z.string().min(1, '预期输出不能为空'),
      assigned_role: z.string().min(1, '分配角色不能为空'),
      dependencies: z.array(z.string()).optional(),
      dynamic_trigger: z.object({
        type: z.enum(['output_contains', 'error_occurred', 'confidence_low', 'custom_llm_call']),
        condition_value: z.union([z.string(), z.array(z.string()), z.number()]),
        dynamic_agent_name: z.string().min(1),
      }).optional(),
    })
  ).min(1, '至少需要一个任务'),
  global_settings: z.object({
    process_type: z.enum(['sequential', 'hierarchical', 'consensus']),
    verbose: z.boolean().optional(),
    manager_llm_model: z.string().optional(),
    manager_agent_id: z.string().optional(),
    crew_memory_enabled: z.boolean().optional(),
    max_rpm: z.number().int().positive().optional(),
    cache_enabled: z.boolean().optional(),
    long_term_memory_enabled: z.boolean().optional(),
    share_crew: z.boolean().optional(),
    state_persistence: z.boolean().optional(),
    human_feedback_enabled: z.boolean().optional(),
  }),
});

export type CreateTeamFormData = z.infer<typeof CreateTeamSchema>;
