import { Briefcase, Newspaper, Users, ShieldAlert, Home, Settings, User, Scale } from "lucide-react";
import { NavLink } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  useSidebar,
} from "@/components/ui/sidebar";

const categories = [
  { title: "일자리 매칭", url: "/chat/job", icon: Briefcase },
  { title: "법률 상담", url: "/chat/legal", icon: Scale },
  { title: "노인 관련 뉴스", url: "/chat/news", icon: Newspaper },
  { title: "종합 노인 복지", url: "/chat/welfare", icon: Users },
  { title: "금융사기탐지", url: "/chat/scam_defense", icon: ShieldAlert },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const isCollapsed = state === "collapsed";

  return (
    <Sidebar collapsible="icon" className="border-r">
      <SidebarHeader className="border-b px-4 py-3">
        <NavLink to="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Home className="h-6 w-6 text-primary-foreground" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="text-2xl font-semibold text-sidebar-foreground">복지팡이</span>
            </div>
          )}
        </NavLink>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-lg font-semibold">카테고리</SidebarGroupLabel>
          <SidebarGroupContent className="text-base">
            <SidebarMenu className="mt-3 gap-3">
              {categories.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    tooltip={item.title}
                    className="gap-3 py-3 text-lg [&_svg]:h-5 [&_svg]:w-5"
                  >
                    <NavLink
                      to={item.url}
                      className={({ isActive }) =>
                        isActive ? "bg-sidebar-accent font-medium" : ""
                      }
                    >
                      <item.icon className="h-5 w-5" />
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-2">
        <SidebarMenu className="gap-2">
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="설정" className="gap-3 py-3 text-lg [&_svg]:h-5 [&_svg]:w-5">
              <Settings className="h-5 w-5" />
              <span>설정</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="사용자" className="gap-3 py-3 text-lg [&_svg]:h-5 [&_svg]:w-5">
              <User className="h-5 w-5" />
              <span>사용자</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
