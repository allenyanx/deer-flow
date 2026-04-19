/**
 * DeerTeamX 根布局
 * 提供 QueryClientProvider 和其他必要的上下文
 */

import { QueryClientProvider } from "@/components/query-client-provider";

export default function DeerTeamXLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <QueryClientProvider>{children}</QueryClientProvider>;
}
