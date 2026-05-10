"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { isAuthenticated } from "@/lib/auth";

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * Tüm korumalı sayfalarda kullanılan ana iskelet.
 * Token yoksa /login'e yönlendirir.
 */
export function AppShell({ children }: AppShellProps) {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  if (!isAuthenticated()) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-screen-xl px-6 py-6">{children}</div>
      </main>
    </div>
  );
}
