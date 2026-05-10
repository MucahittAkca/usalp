import { AppShell } from "@/components/layout/AppShell";
import { ServerList } from "@/components/servers/ServerList";

export default function HomePage() {
  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        {/* Sayfa başlığı */}
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Genel Bakış</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Tüm sunucularınızın anlık durumu
          </p>
        </div>

        {/* Sunucu listesi — 30 sn polling ile */}
        <ServerList />
      </div>
    </AppShell>
  );
}
