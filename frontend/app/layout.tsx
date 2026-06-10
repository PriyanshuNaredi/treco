import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Treco — Real-time observability for AI agents",
  description: "See what your AI coding agents are doing in real time. Live kanban, acceptance criteria tracking, token cost per session. Open source.",
  openGraph: {
    title: "Treco — Real-time observability for AI agents",
    description: "See what your AI coding agents are doing in real time. Live kanban, acceptance criteria tracking, token cost per session. Open source.",
    url: "https://treco.dev",
    siteName: "Treco",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Treco — Real-time observability for AI agents",
    description: "See what your AI coding agents are doing in real time.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-[var(--bg)] text-[var(--text)]">
        {children}
      </body>
    </html>
  );
}
