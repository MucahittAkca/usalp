interface ServerDetailPageProps {
  params: { id: string };
}

export default function ServerDetailPage({ params }: ServerDetailPageProps) {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Sunucu Detay — #{params.id}</h1>
      {/* TODO(v1): Metrik grafikleri, servis durumları, log tablosu */}
    </main>
  );
}
