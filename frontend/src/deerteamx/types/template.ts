/**
 * DeerTeamX 类型定义 - 模板相关
 * 严格对齐后端 API_REFERENCE.md 第5节
 */

/**
 * 模板范围枚举
 */
export type TemplateScope = 'personal' | 'system';

/**
 * 模板摘要
 */
export interface TemplateSummary {
  template_id: string;
  template_name: string;
  description?: string;
  scope: TemplateScope;
  usage_count: number;
  creator_name: string;
}

/**
 * 保存为模板请求
 */
export interface SaveAsTemplateRequest {
  team_id: string;
  template_name: string;
  description?: string;
  scope: TemplateScope;
}

/**
 * 保存为模板响应
 */
export interface SaveAsTemplateResponse {
  template_id: string;
  template_name: string;
  scope: TemplateScope;
  created_at: string;
}

/**
 * 使用模板请求
 */
export interface UseTemplateRequest {
  team_name: string;
  overrides?: {
    roles?: Array<{
      role_id: string;
      model?: string;
    }>;
  };
}

/**
 * 使用模板响应
 */
export interface UseTemplateResponse {
  team_id: string;
  version: string;
}

/**
 * 模板列表响应
 */
export interface TemplateListResponse {
  templates: TemplateSummary[];
}
