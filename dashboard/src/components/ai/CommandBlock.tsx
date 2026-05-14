"use client";

import { useState } from "react";
import { Check, Copy, ShieldAlert } from "lucide-react";
import {
  COMMAND_RISK_COLORS,
  COMMAND_RISK_LABELS,
  cn,
} from "@/lib/utils";
import type { CommandSuggestion } from "@/types/api";

interface CommandBlockProps {
  command: CommandSuggestion;
}

export function CommandBlock({ command }: CommandBlockProps) {
  const [copied, setCopied] = useState(false);
  const riskClass =
    COMMAND_RISK_COLORS[command.risk_level] ??
    "border-slate-200 bg-slate-50 text-slate-600";
  const riskLabel = COMMAND_RISK_LABELS[command.risk_level] ?? command.risk_level;

  function handleCopy() {
    navigator.clipboard.writeText(command.command).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-700 bg-slate-900">
      {/* Komut satırı */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
        <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-sm text-green-400">
          {command.command}
        </code>
        <div className="flex shrink-0 items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold",
              riskClass,
            )}
          >
            <ShieldAlert size={11} />
            {riskLabel}
          </span>
          <button
            onClick={handleCopy}
            className="rounded p-1 text-slate-400 hover:bg-slate-700 hover:text-slate-200 transition-colors"
            aria-label={copied ? "Kopyalandı" : `${command.command} komutunu kopyala`}
          >
            {copied ? (
              <Check size={14} className="text-green-400" />
            ) : (
              <Copy size={14} />
            )}
          </button>
        </div>
      </div>

      {/* Açıklama */}
      {command.description && (
        <div className="border-t border-slate-700/60 bg-slate-800/50 px-4 py-1.5">
          <p className="text-xs text-slate-400">{command.description}</p>
        </div>
      )}
    </div>
  );
}
