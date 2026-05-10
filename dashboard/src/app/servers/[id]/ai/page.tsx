import { AppShell } from "@/components/layout/AppShell";
import { AnalysisPanel } from "@/components/ai/AnalysisPanel";

interface AiPageProps {
  params: { id: string };
}

export default function ServerAiPage({ params }: AiPageProps) {
  const serverId = Number(params.id);

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl px-4 py-8">
        <AnalysisPanel serverId={serverId} />
      </div>
    </AppShell>
  );
}
