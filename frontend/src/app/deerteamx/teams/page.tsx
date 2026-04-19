/**
 * DeerTeamX 团队列表页
 * 路由：/deerteamx/teams
 */

'use client';

import { useState } from 'react';
import { useTeams } from '../../../deerteamx/hooks/useTeams';
import { TeamList } from '../../../deerteamx/components/teams/TeamList';
import { PermissionGuard } from '../../../deerteamx/components/shared/PermissionGuard';

export default function TeamsPage() {
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card');
  const [filters, setFilters] = useState<{ status?: string; keyword?: string }>({});

  const { data, isLoading, error } = useTeams({
    page: 1,
    page_size: 20,
    ...filters,
  });

  // TODO: 实现团队列表页
  // - 顶部操作区：新建团队按钮、导入CrewAI配置、视图切换、筛选器
  // - 列表展示区：TeamList 组件
  // - 权限控制：通过 PermissionGuard 控制操作按钮显隐
  
  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">团队中心</h1>
        <div className="text-center py-8">加载中...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">团队中心</h1>
        <div className="text-red-500 py-8">
          加载失败: {error.message}
          <div className="text-sm text-gray-500 mt-2">
            请检查:
            <ul className="list-disc list-inside mt-2">
              <li>后端服务是否启动 (默认 http://localhost:8000)</li>
              <li>是否已登录 (需要 access_token)</li>
              <li>环境变量 NEXT_PUBLIC_DEERTEAMX_API_URL 是否正确配置</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      {/* 页面头部操作区 */}
      <header className="mb-6 flex justify-between items-center">
        <h1 className="text-3xl font-bold">团队中心</h1>
        
        <div className="flex gap-2">
          <PermissionGuard resource="team" action="create">
            <button className="px-4 py-2 bg-blue-500 text-white rounded">
              新建团队
            </button>
          </PermissionGuard>
          
          <PermissionGuard resource="team" action="import">
            <button className="px-4 py-2 border rounded">
              导入CrewAI配置
            </button>
          </PermissionGuard>
        </div>
      </header>

      {/* 团队列表 */}
      <TeamList
        teams={data?.teams || []}
        viewMode={viewMode}
        loading={isLoading}
        onEdit={(teamId) => {
          // TODO: 路由跳转至编辑页
          console.log('Edit team:', teamId);
        }}
        onDelete={(teamId) => {
          // TODO: 删除确认
          console.log('Delete team:', teamId);
        }}
        onExecute={(teamId) => {
          // TODO: 触发执行
          console.log('Execute team:', teamId);
        }}
      />
    </div>
  );
}
