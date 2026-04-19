/**
 * DeerTeamX 团队列表组件骨架
 * 支持卡片视图/表格视图切换
 */

'use client';

import type { TeamSummary } from '../../types';
import { TeamCard } from './TeamCard';

interface TeamListProps {
  teams: TeamSummary[];
  viewMode?: 'card' | 'table';
  loading?: boolean;
  onEdit?: (teamId: string) => void;
  onDelete?: (teamId: string) => void;
  onExecute?: (teamId: string) => void;
}

export function TeamList({
  teams,
  viewMode = 'card',
  loading = false,
  onEdit,
  onDelete,
  onExecute,
}: TeamListProps) {
  // TODO: 实现团队列表
  // - 卡片视图：响应式网格布局（grid-cols-1 md:grid-cols-2 lg:grid-cols-3）
  // - 表格视图：Ant Design Table 组件
  // - 加载态：Skeleton 骨架屏
  // - 空态：Ant Design Empty 组件
  
  if (loading) {
    return <div>Loading...</div>; // TODO: 替换为 Skeleton
  }

  if (teams.length === 0) {
    return <div>No teams found</div>; // TODO: 替换为 Empty
  }

  if (viewMode === 'card') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map((team) => (
          <TeamCard
            key={team.team_id}
            team={team}
            onEdit={onEdit}
            onDelete={onDelete}
            onExecute={onExecute}
          />
        ))}
      </div>
    );
  }

  // TODO: 表格视图实现
  return <div>Table view not implemented yet</div>;
}
