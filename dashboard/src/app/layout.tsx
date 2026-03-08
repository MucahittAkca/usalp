import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Usalp — Sunucu İzleme",
  description: "AI destekli sunucu izleme ve log analiz platformu",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
