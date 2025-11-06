import { Briefcase, Newspaper, Users, ShieldAlert, Home, Scale } from "lucide-react";
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
          <div className="flex h-9 w-9 items-center ">
            <img src="/favicon.png" alt="홈" className="h-full w-full object-cover" />
          </div>
          {!isCollapsed && (
            <img
              src="/logo.png"
              alt="복지팡이 로고"
              className="h-14 w-auto object-contain"
            />
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

      <SidebarFooter className="border-t p-2" />
    </Sidebar>
  );
}
