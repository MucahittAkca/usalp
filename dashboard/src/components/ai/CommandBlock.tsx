"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import type { CommandSuggestion } from "@/types/api";

interface CommandBlockProps {
  command: CommandSuggestion;
}

export function CommandBlock({ command }: CommandBlockProps) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(command.command).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-700 bg-slate-900">
      {/* Komut satırı */}
      <div className="flex items-center justify-between gap-3 px-4 py-2.5">
        <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-sm text-green-400">
          {command.command}
        </code>
        <button
          onClick={handleCopy}
          className="shrink-0 rounded p-1 text-slate-400 hover:bg-slate-700 hover:text-slate-200 transition-colors"
          aria-label={copied ? "Kopyalandı" : `${command.command} komutunu kopyala`}
        >
          {copied ? (
            <Check size={14} className="text-green-400" />
          ) : (
            <Copy size={14} />
          )}
        </button>
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
