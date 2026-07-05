"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ModeToggle } from "@/components/ModeToggle";
import {
  LayoutDashboard,
  Search,
  Briefcase,
  Bell,
  LogOut,
  Users,
  FileText,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const creatorNav: NavItem[] = [
  { href: "/creator/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/creator/discovery", label: "Find Brands", icon: Search },
  { href: "/creator/connections", label: "Connections", icon: Users },
  { href: "/creator/profile", label: "My Profile", icon: User },
];

const brandNav: NavItem[] = [
  { href: "/brand/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/brand/discover", label: "Find Creators", icon: Search },
  { href: "/brand/campaigns", label: "Campaigns", icon: FileText },
  { href: "/brand/connections", label: "Connections", icon: Users },
  { href: "/brand/profile", label: "My Profile", icon: User },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const navItems = user?.role === "creator" ? creatorNav : brandNav;
  const initials = user?.name
    ? user.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "?";
  const profileLink = user?.role === "creator" ? "/creator/profile" : "/brand/profile";

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 bg-white border-r border-slate-100 flex flex-col">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-slate-100">
          <span className="font-outfit font-bold text-xl text-slate-800">
            Nex<span className="text-indigo-600">us</span>
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-800"
                )}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="px-3 pb-4 border-t border-slate-100 pt-4">
          <Link href={profileLink} className="flex items-center gap-3 px-3 py-2 mb-2 hover:bg-slate-50 rounded-xl transition-colors cursor-pointer">
            <Avatar className="w-8 h-8">
              <AvatarImage src={user?.avatar_url ?? undefined} />
              <AvatarFallback className="text-xs bg-indigo-100 text-indigo-700">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">
                {user?.name}
              </p>
              <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
            </div>
          </Link>
          <button
            onClick={logout}
            className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm text-slate-500 hover:bg-slate-50 hover:text-slate-700 w-full transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="bg-white border-b border-slate-100 px-8 py-4 flex items-center justify-between">
          <div />
          <div className="flex items-center gap-2">
            <ModeToggle />
            <Link href={user?.role === "creator" ? "/creator/notifications" : "/brand/notifications"}>
              <Button variant="ghost" size="icon" className="rounded-xl">
                <Bell className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 px-8 py-8 max-w-5xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
