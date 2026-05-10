"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ServerList } from "@/components/servers/ServerList";
import { AddServerModal } from "@/components/servers/AddServerModal";

export default function ServersPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Sunucular</h1>
            <p className="mt-0.5 text-sm text-slate-500">
              Sisteme kayıtlı tüm sunucular
            </p>
          </div>
          <AddServerModal onCreated={() => setRefreshKey((k) => k + 1)} />
        </div>

        <ServerList key={refreshKey} />
      </div>
    </AppShell>
  );
}
