/**
 * DeerTeamX 格式化工具函数
 */

/**
 * 格式化日期时间为本地字符串
 */
export function formatDateTime(isoString: string): string {
  if (!isoString) return '-';
  return new Date(isoString).toLocaleString('zh-CN');
}

/**
 * 格式化 Token 数量（添加千位分隔符）
 */
export function formatTokenCount(count: number): string {
  return count.toLocaleString();
}

/**
 * 格式化耗时（毫秒转可读格式）
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}min`;
}

/**
 * 格式化版本号（语义化版本校验）
 */
export function isValidSemver(version: string): boolean {
  const semverRegex = /^v?\d+\.\d+\.\d+$/;
  return semverRegex.test(version);
}

/**
 * 截断文本（超出长度显示省略号）
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}
