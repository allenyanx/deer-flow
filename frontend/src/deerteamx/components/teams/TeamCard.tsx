/**
 * DeerTeamX 团队卡片组件骨架
 * 复用 @/components/ui/card, @/components/ui/button
 */

'use client';

import type { TeamSummary } from '../../types';

interface TeamCardProps {
  team: TeamSummary;
  onEdit?: (teamId: string) => void;
  onDelete?: (teamId: string) => void;
  onExecute?: (teamId: string) => void;
}

export function TeamCard({ team, onEdit, onDelete, onExecute }: TeamCardProps) {
  // TODO: 实现团队卡片UI
  // - 复用 Ant Design Card 组件
  // - 展示团队名称、模式标签、状态徽标
  // - 操作按钮：执行/编辑/删除（通过 PermissionGuard 控制）
  // - Hover 效果：阴影过渡
  
  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow">
      {/* TODO: 卡片内容 */}
      <h3 className="text-lg font-semibold">{team.name}</h3>
      <p className="text-sm text-muted-foreground">{team.execution_mode}</p>
      <div className="mt-4 flex gap-2">
        {/* TODO: 操作按钮 */}
      </div>
    </div>
  );
}
