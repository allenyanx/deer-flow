"use client";

import { BotIcon, Briefcase, Building2, Layers, MessagesSquare, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
} from "@/components/ui/sidebar";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/core/i18n/hooks";

// 执行中任务角标组件
function ExecutionBadge() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    // TODO: 实现 WebSocket 订阅 badge_update 事件
    // 暂时使用模拟数据
    const fetchRunningCount = async () => {
      try {
        const response = await fetch('/api/v1/organizations/executions/running-count');
        if (response.ok) {
          const data = await response.json();
          setCount(data.count || 0);
        }
      } catch (error) {
        console.error('Failed to fetch running executions count:', error);
      }
    };
    
    fetchRunningCount();
    
    // 每15秒轮询一次（降级策略）
    const interval = setInterval(fetchRunningCount, 15000);
    
    return () => clearInterval(interval);
  }, []);
  
  if (count === 0) return null;
  
  return (
    <Badge variant="destructive" className="ml-auto text-xs">
      {count > 99 ? '99+' : count}
    </Badge>
  );
}

export function WorkspaceNavChatList() {
  const { t } = useI18n();
  const pathname = usePathname();
  const [isOrgOpen, setIsOrgOpen] = useState(true); // 默认展开
  
  // 判断当前是否在组织中心路由下
  const isOrganizationRoute = pathname?.startsWith('/organization');
  const isCompanyRoute = pathname?.startsWith('/organization/company');
  const isDepartmentRoute = pathname?.startsWith('/organization/department');
  const isTeamRoute = pathname?.startsWith('/organization/team');
  
  // 如果当前在组织中心路由下，自动展开
  useEffect(() => {
    if (isOrganizationRoute) {
      setIsOrgOpen(true);
    }
  }, [isOrganizationRoute]);
  
  return (
    <SidebarGroup className="pt-1">
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton isActive={pathname === "/workspace/chats"} asChild>
            <Link className="text-muted-foreground" href="/workspace/chats">
              <MessagesSquare />
              <span>{t.sidebar.chats}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/agents")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/agents">
              <BotIcon />
              <span>{t.sidebar.agents}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        
        {/* [修订 v1.0.16] 组织中心（原团队中心升级） */}
        <SidebarMenuItem>
          <Collapsible open={isOrgOpen} onOpenChange={setIsOrgOpen} className="w-full">
            <CollapsibleTrigger asChild>
              <SidebarMenuButton 
                isActive={isOrganizationRoute}
                className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              >
                <Layers />
                <span>组织中心</span>
                {isOrgOpen ? (
                  <ChevronDown className="ml-auto size-4" />
                ) : (
                  <ChevronRight className="ml-auto size-4" />
                )}
              </SidebarMenuButton>
            </CollapsibleTrigger>
            
            <CollapsibleContent>
              <SidebarMenuSub>
                {/* 公司管理 */}
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton 
                    asChild
                    isActive={isCompanyRoute}
                  >
                    <Link href="/organization/company">
                      <Building2 className="size-3" />
                      <span>公司管理</span>
                    </Link>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                
                {/* 部门管理 */}
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton 
                    asChild
                    isActive={isDepartmentRoute}
                  >
                    <Link href="/organization/department">
                      <Briefcase className="size-3" />
                      <span>部门管理</span>
                    </Link>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                
                {/* 团队管理（带角标） */}
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton 
                    asChild
                    isActive={isTeamRoute}
                  >
                    <Link href="/organization/team">
                      <Users className="size-3" />
                      <span>团队管理</span>
                      <ExecutionBadge />
                    </Link>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </CollapsibleContent>
          </Collapsible>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroup>
  );
}
