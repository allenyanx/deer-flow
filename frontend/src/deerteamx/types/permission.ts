/**
 * DeerTeamX 类型定义 - 权限相关
 * 严格对齐后端 API_REFERENCE.md 第2节 & 权限系统实现方案
 */

/**
 * 角色类型枚举
 */
export type RoleType = 'developer' | 'researcher' | 'enthusiast';

/**
 * 权限矩阵结构
 */
export interface PermissionMatrix {
  team: {
    list: boolean;
    create: boolean;
    edit: boolean;
    delete: boolean;
    execute: boolean;
    import: boolean;
  };
  template: {
    list: boolean;
    use: boolean;
    create: boolean;
    edit: boolean;
    delete: boolean;
  };
  export: {
    result: boolean;
  };
}

/**
 * 权限响应
 */
export interface PermissionResponse {
  role_type: RoleType;
  permissions: PermissionMatrix;
}

/**
 * 角色切换请求
 */
export interface RoleUpdateRequest {
  role_type: RoleType;
}

/**
 * 角色切换响应
 */
export interface RoleUpdateResponse {
  access_token: string;
  role_type: RoleType;
}
