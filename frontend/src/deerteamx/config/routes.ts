/**
 * DeerTeamX 路由配置
 * 包含权限守卫元数据
 */

export interface RouteConfig {
  path: string;
  label: string;
  permission?: {
    resource: string;
    action: string;
  };
  children?: RouteConfig[];
}

export const routes: RouteConfig[] = [
  {
    path: '/deerteamx/teams',
    label: '团队中心',
    permission: {
      resource: 'team',
      action: 'list',
    },
    children: [
      {
        path: '/deerteamx/teams/new',
        label: '新建团队',
        permission: {
          resource: 'team',
          action: 'create',
        },
      },
      {
        path: '/deerteamx/teams/[teamId]',
        label: '团队详情',
        permission: {
          resource: 'team',
          action: 'edit',
        },
      },
    ],
  },
  {
    path: '/deerteamx/executions',
    label: '执行历史',
    permission: {
      resource: 'team',
      action: 'list',
    },
  },
  {
    path: '/deerteamx/templates',
    label: '模板库',
    permission: {
      resource: 'template',
      action: 'list',
    },
  },
];
