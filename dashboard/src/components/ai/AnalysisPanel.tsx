"use client";

import { Brain, Clock, FileText, RefreshCw, Terminal } from "lucide-react";
import { useAiAnalysis } from "@/hooks/useAiAnalysis";
import { ConfidenceBar } from "./ConfidenceBar";
import { CauseList } from "./CauseList";
import { CommandBlock } from "./CommandBlock";
import { SEVERITY_COLORS, SEVERITY_LABELS, formatDateTime, cn } from "@/lib/utils";
import type { AiAnalysis, AiCategory } from "@/types/api";

// ---------------------------------------------------------------------------
// Yardımcı sabitler
// ---------------------------------------------------------------------------

const CATEGORY_LABELS: Record<AiCategory, string> = {
  network_error:        "Ağ Hatası",
  disk_issue:           "Disk Sorunu",
  permission_issue:     "İzin Hatası",
  config_error:         "Yapılandırma Hatası",
  dependency_failure:   "Bağımlılık Hatası",
  resource_exhaustion:  "Kaynak Tükenmesi",
  unknown:              "Bilinmiyor",
};

// ---------------------------------------------------------------------------
// AnalysisCard — tek bir analizi gösterir
// ---------------------------------------------------------------------------

function AnalysisCard({ analysis, highlight }: { analysis: AiAnalysis; highlight?: boolean }) {
  const severityClass = SEVERITY_COLORS[analysis.severity] ?? "text-slate-600 bg-slate-50 border-slate-200";

  return (
    <div
      className={cn(
        "rounded-xl border p-5 space-y-5 transition-shadow",
        highlight
          ? "border-blue-200 bg-white shadow-md"
          : "border-slate-100 bg-slate-50/60",
      )}
    >
      {/* Başlık satırı */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {CATEGORY_LABELS[analysis.category] ?? analysis.category}
          </p>
          <p className="text-sm font-medium text-slate-800 leading-snug max-w-xl">
            {analysis.summary}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
              severityClass,
            )}
          >
            {SEVERITY_LABELS[analysis.severity] ?? analysis.severity}
          </span>
        </div>
      </div>

      {/* Güven skoru */}
      <ConfidenceBar value={analysis.confidence} />

      {/* Olası nedenler */}
      <CauseList causes={analysis.causes} />

      {/* Kanıt satırları */}
      {analysis.evidence_lines.length > 0 && (
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
            <FileText size={11} />
            Kanıt Satırları
          </h4>
          <div className="space-y-1.5">
            {analysis.evidence_lines.map((line, i) => (
              <div
                key={i}
                className="rounded-md border border-slate-200 bg-white px-3 py-2"
              >
                <code className="block whitespace-pre-wrap break-words font-mono text-xs leading-5 text-slate-600">
                  {line}
                </code>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Önerilen komutlar */}
      {analysis.commands.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400 flex items-center gap-1.5">
            <Terminal size={11} />
            Önerilen Komutlar
          </h4>
          <div className="space-y-2">
            {analysis.commands.map((cmd, i) => (
              <CommandBlock key={i} command={cmd} />
            ))}
          </div>
        </div>
      )}

      {/* Analiz zamanı */}
      <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
        <Clock size={10} />
        <time dateTime={analysis.created_at}>
          {formatDateTime(analysis.created_at)}
        </time>
        {analysis.alert_id && (
          <span className="ml-2 text-slate-300">· Alert #{analysis.alert_id}</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AnalysisPanel — ana bileşen
// ---------------------------------------------------------------------------

interface AnalysisPanelProps {
  serverId: number;
}

export function AnalysisPanel({ serverId }: AnalysisPanelProps) {
  const {
    analyses,
    latest,
    isLoading,
    error,
    mutate,
    trigger,
    triggering,
    cooldownError,
    triggerError,
  } = useAiAnalysis(serverId);

  return (
    <div className="space-y-6">
      {/* Üst bölüm — başlık + tetikle butonu */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Brain size={18} className="text-blue-500" />
          <h2 className="text-base font-semibold text-slate-800">AI Analiz Paneli</h2>
          {analyses.length > 0 && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
              {analyses.length} analiz
            </span>
          )}
        </div>

        <button
          onClick={() => trigger()}
          disabled={triggering}
          className={cn(
            "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all",
            triggering
              ? "cursor-not-allowed bg-slate-100 text-slate-400"
              : "bg-blue-600 text-white hover:bg-blue-700 active:scale-95 shadow-sm",
          )}
          aria-label="Yeni AI analizi başlat"
        >
          <RefreshCw size={14} className={triggering ? "animate-spin" : ""} />
          {triggering ? "Analiz ediliyor…" : "Yeni Analiz Başlat"}
        </button>
      </div>

      {/* Bildirimler */}
      {cooldownError && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-700">
          Bu sunucu için çok yakın zamanda analiz yapıldı. Lütfen 5 dakika bekleyin.
        </div>
      )}
      {triggerError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {triggerError}
        </div>
      )}

      {/* Yükleniyor */}
      {isLoading && (
        <div className="space-y-3">
          {[0, 1].map((i) => (
            <div key={i} className="h-52 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      )}

      {/* Hata */}
      {error && !isLoading && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-red-100 bg-red-50 py-12 text-center">
          <p className="text-sm text-red-600">Analizler yüklenemedi.</p>
          <button
            onClick={() => mutate()}
            className="text-xs text-red-500 underline hover:no-underline"
          >
            Tekrar dene
          </button>
        </div>
      )}

      {/* Veri var */}
      {!isLoading && !error && (
        <>
          {/* En son analiz — vurgulanmış */}
          {latest ? (
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                En Son Analiz
              </p>
              <AnalysisCard analysis={latest} highlight />
            </div>
          ) : (
            /* Boş durum */
            <div className="flex flex-col items-center gap-3 rounded-xl border-2 border-dashed border-slate-200 py-16 text-center">
              <Brain size={32} className="text-slate-300" />
              <div>
                <p className="font-medium text-slate-500">Henüz analiz yapılmamış</p>
                <p className="mt-1 text-xs text-slate-400">
                  &ldquo;Yeni Analiz Başlat&rdquo; butonuna tıklayarak ilk AI analizini başlatın.
                </p>
              </div>
            </div>
          )}

          {/* Geçmiş analizler */}
          {analyses.length > 1 && (
            <div className="space-y-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Geçmiş Analizler
              </p>
              {analyses.slice(1).map((a) => (
                <AnalysisCard key={a.id} analysis={a} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
