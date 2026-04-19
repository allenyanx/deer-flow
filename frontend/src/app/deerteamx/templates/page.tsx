/**
 * DeerTeamX 模板库页
 * 路由：/deerteamx/templates
 */

'use client';

import { useTemplates } from '../../../deerteamx/hooks/useTemplates';

export default function TemplatesPage() {
  const { data, isLoading, error } = useTemplates({
    scope: 'all',
  });

  // TODO: 实现模板库页
  // - 网格布局展示模板卡片
  // - 筛选器：系统模板/个人模板
  // - 点击使用模板创建团队
  
  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error loading templates</div>;
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">模板库</h1>
      
      {/* TODO: 模板网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {data?.templates.map((template) => (
          <div key={template.template_id} className="border rounded p-4">
            <h3 className="font-semibold">{template.template_name}</h3>
            <p className="text-sm text-muted-foreground">{template.scope}</p>
            {/* TODO: 使用模板按钮 */}
          </div>
        ))}
      </div>
    </div>
  );
}
