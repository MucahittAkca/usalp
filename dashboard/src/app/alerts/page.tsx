import { AppShell } from "@/components/layout/AppShell";
import { AlertList } from "@/components/alerts/AlertList";

export default function AlertsPage() {
  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Alarm Merkezi</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Aktif alarmları görüntüleyin ve çözüldü olarak işaretleyin
          </p>
        </div>

        <AlertList />
      </div>
    </AppShell>
  );
}
