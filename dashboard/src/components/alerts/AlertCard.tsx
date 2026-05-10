"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, ExternalLink, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { AlertSeverityBadge, AlertTypeBadge } from "@/components/alerts/AlertBadge";
import { cn, formatDateTime } from "@/lib/utils";
import type { Alert } from "@/types/api";

interface AlertCardProps {
  alert: Alert;
  /** Çözümlendiğinde listeyi yenilemek için çağrılır */
  onResolved: () => void;
}

export function AlertCard({ alert, onResolved }: AlertCardProps) {
  const [resolving, setResolving] = useState(false);
  const [resolved, setResolved] = useState(false);

  const isActive = alert.resolved_at === null;

  async function handleResolve() {
    if (resolving || resolved) return;
    setResolving(true);
    try {
      await api.alerts.resolve(alert.id);
      setResolved(true);
      // Kısa gecikme sonrası listeyi yenile — kullanıcı geri bildirimi görsün
      setTimeout(onResolved, 600);
    } catch {
      // Hata durumunda sessizce geri dön — liste polling ile zaten güncellenecek
    } finally {
      setResolving(false);
    }
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-xl border bg-white p-4 shadow-sm transition-opacity",
        !isActive && "opacity-60",
        resolved && "opacity-40",
      )}
    >
      {/* Üst satır: badge'ler + zaman */}
      <div className="flex flex-wrap items-center gap-2">
        <AlertSeverityBadge severity={alert.severity} />
        <AlertTypeBadge type={alert.type} />
        <span className="ml-auto text-xs text-slate-400">
          {formatDateTime(alert.created_at)}
        </span>
      </div>

      {/* Alarm mesajı */}
      <p className="text-sm text-slate-800 leading-relaxed">{alert.message}</p>

      {/* Alt satır: sunucu linki + çözüm butonu */}
      <div className="flex items-center justify-between gap-2">
        <Link
          href={`/servers/${alert.server_id}`}
          className="inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 hover:underline"
          aria-label={`Sunucu ${alert.server_id} detayına git`}
        >
          <ExternalLink size={11} />
          Sunucu #{alert.server_id}
        </Link>

        {isActive && !resolved && (
          <button
            onClick={handleResolve}
            disabled={resolving}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              "bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50",
            )}
            aria-label="Alarmı çözüldü olarak işaretle"
          >
            {resolving ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Check size={12} />
            )}
            Çözüldü olarak işaretle
          </button>
        )}

        {(resolved || !isActive) && (
          <span className="inline-flex items-center gap-1 text-xs text-green-600">
            <Check size={12} />
            {resolved ? "Çözüldü" : `Çözüldü — ${formatDateTime(alert.resolved_at!)}`}
          </span>
        )}
      </div>
    </div>
  );
}
