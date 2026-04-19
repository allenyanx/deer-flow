/**
 * DeerTeamX 团队编辑器核心组件骨架
 * 包含角色配置、任务编排、DAG画布
 */

'use client';

import type { Team } from '../../types';

interface TeamEditorProps {
  teamId?: string; // 新建时为 undefined
  initialData?: Partial<Team>;
  onSave?: (data: Partial<Team>) => void;
  onCancel?: () => void;
}

export function TeamEditor({ teamId, initialData, onSave, onCancel }: TeamEditorProps) {
  // TODO: 实现团队编辑器
  // - 左侧锚点导航：基础信息/角色配置/任务编排/技能绑定
  // - 右侧表单区域：React Hook Form + Zod 校验
  // - DAG 画布：AntV X6 可视化依赖关系
  // - 版本管理：语义化版本自动递增
  
  return (
    <div className="flex h-full">
      {/* TODO: 左侧导航 */}
      <aside className="w-64 border-r">
        <nav>
          {/* TODO: 锚点导航项 */}
        </nav>
      </aside>

      {/* TODO: 右侧内容区 */}
      <main className="flex-1 p-6 overflow-auto">
        <h2 className="text-2xl font-bold mb-4">
          {teamId ? '编辑团队' : '新建团队'}
        </h2>
        
        {/* TODO: 表单内容 */}
        <form>
          {/* 基础信息 */}
          <div className="mb-6">
            <label className="block mb-2">团队名称</label>
            <input type="text" className="w-full border rounded px-3 py-2" />
          </div>

          {/* TODO: 角色配置、任务编排等 */}
        </form>
      </main>
    </div>
  );
}
