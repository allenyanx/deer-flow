/**
 * DeerTeamX API 客户端 - Templates
 * 对齐 @/core/api 风格,严格遵循后端接口定义
 */

import type {
  TemplateSummary,
  TemplateListResponse,
  SaveAsTemplateRequest,
  SaveAsTemplateResponse,
  UseTemplateRequest,
  UseTemplateResponse,
} from '../types';

const DEERTEAMX_BASE_URL =
  process.env.NEXT_PUBLIC_DEERTEAMX_API_URL || 'http://localhost:8000';

/**
 * 获取认证Token
 */
function getAuthToken(): string {
  return typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
}

/**
 * 保存为模板
 */
export async function saveAsTemplate(
  data: SaveAsTemplateRequest
): Promise<SaveAsTemplateResponse> {
  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/templates`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getAuthToken()}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to save as template: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 列出模板
 */
export async function listTemplates(params?: {
  scope?: 'system' | 'personal' | 'all';
  keyword?: string;
}): Promise<TemplateListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.scope) queryParams.set('scope', params.scope);
  if (params?.keyword) queryParams.set('keyword', params.keyword);

  const response = await fetch(`${DEERTEAMX_BASE_URL}/api/v1/templates?${queryParams}`, {
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to list templates: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 使用模板创建团队
 */
export async function useTemplate(
  templateId: string,
  data: UseTemplateRequest
): Promise<UseTemplateResponse> {
  const response = await fetch(
    `${DEERTEAMX_BASE_URL}/api/v1/templates/${templateId}/use`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to use template: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}
