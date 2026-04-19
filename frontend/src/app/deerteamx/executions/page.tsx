/**
 * DeerTeamX 执行历史列表页
 * 路由：/deerteamx/executions
 */

'use client';

import { useExecutions } from '../../../deerteamx/hooks/useExecutions';

export default function ExecutionsPage() {
  const { data, isLoading, error } = useExecutions({
    limit: 50,
    offset: 0,
  });

  // TODO: 实现执行历史列表页
  // - 顶部筛选器：按团队、状态筛选
  // - 列表展示：执行ID、团队名称、状态、Token消耗、耗时
  // - 点击跳转至执行详情页
  
  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error loading executions</div>;
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">执行历史</h1>
      
      {/* TODO: 执行列表 */}
      <div className="space-y-4">
        {data?.executions.map((execution) => (
          <div key={execution.execution_id} className="border rounded p-4">
            <h3 className="font-semibold">{execution.execution_id}</h3>
            <p>Status: {execution.status}</p>
            {/* TODO: 更多字段展示 */}
          </div>
        ))}
      </div>
    </div>
  );
}
