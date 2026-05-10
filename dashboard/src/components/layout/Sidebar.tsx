"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  Bot,
  LayoutDashboard,
  Server,
  type LucideIcon,
} from "lucide-react";
import { clsx } from "clsx";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  matchPrefix?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Genel Bakış",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Sunucular",
    href: "/servers",
    icon: Server,
    matchPrefix: true,
  },
  {
    label: "Alarmlar",
    href: "/alerts",
    icon: AlertTriangle,
    matchPrefix: true,
  },
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.matchPrefix) {
    return pathname.startsWith(item.href);
  }
  return pathname === item.href;
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-slate-200 bg-white">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2.5 border-b border-slate-200 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
          <Activity size={16} className="text-white" />
        </div>
        <span className="text-[15px] font-semibold tracking-tight text-slate-900">
          Usalp
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-0.5" role="list">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={clsx(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-brand-50 text-brand-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon
                    size={16}
                    className={clsx(
                      active ? "text-brand-600" : "text-slate-400",
                    )}
                  />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-200 px-5 py-4">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Bot size={13} />
          <span>AI analiz aktif</span>
        </div>
      </div>
    </aside>
  );
}
