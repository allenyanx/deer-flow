/**
 * DeerTeamX 团队详情页
 * 路由：/deerteamx/teams/[teamId]
 */

'use client';

import { useParams } from 'next/navigation';
import { useTeam } from '../../../deerteamx/hooks/useTeams';
import { TeamEditor } from '../../../deerteamx/components/teams/TeamEditor';

export default function TeamDetailPage() {
  const params = useParams();
  const teamId = params.teamId as string;

  const { data: team, isLoading, error } = useTeam(teamId);

  // TODO: 实现团队详情页
  // - 加载态：Skeleton
  // - 错误态：Error 提示
  // - 成功态：TeamEditor 组件（只读或编辑模式）
  
  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error loading team</div>;
  }

  return (
    <div className="h-screen">
      <TeamEditor
        teamId={teamId}
        initialData={team}
        onSave={(data) => {
          // TODO: 保存逻辑
          console.log('Save team:', data);
        }}
        onCancel={() => {
          // TODO: 返回团队列表
          console.log('Cancel edit');
        }}
      />
    </div>
  );
}
