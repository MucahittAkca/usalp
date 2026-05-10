interface CauseListProps {
  causes: string[];
}

export function CauseList({ causes }: CauseListProps) {
  if (causes.length === 0) return null;

  return (
    <div>
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Olası Nedenler
      </h4>
      <ol className="space-y-2" role="list">
        {causes.map((cause, i) => (
          <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700">
            <span
              className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-500"
              aria-hidden="true"
            >
              {i + 1}
            </span>
            {cause}
          </li>
        ))}
      </ol>
    </div>
  );
}
