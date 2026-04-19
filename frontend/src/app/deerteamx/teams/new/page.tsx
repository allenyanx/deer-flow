/**
 * DeerTeamX 新建团队页
 * 路由：/deerteamx/teams/new
 */

'use client';

import { useRouter } from 'next/navigation';
import { TeamEditor } from '../../../deerteamx/components/teams/TeamEditor';

export default function NewTeamPage() {
  const router = useRouter();

  // TODO: 实现新建团队页
  // - 复用 TeamEditor 组件（teamId 为空）
  // - 保存成功后跳转至团队详情页
  // - 取消后返回团队列表
  
  return (
    <div className="h-screen">
      <TeamEditor
        onSave={(data) => {
          // TODO: 调用 createTeam API
          console.log('Create team:', data);
          // router.push(`/deerteamx/teams/${newTeamId}`);
        }}
        onCancel={() => {
          router.back();
        }}
      />
    </div>
  );
}
