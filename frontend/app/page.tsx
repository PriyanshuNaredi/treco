"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";

const GITHUB_URL = "https://github.com/danfranco3/treco";

function FadeUp({ children, className, delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const reduced = useReducedMotion();
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={reduced ? false : { opacity: 0, y: 28 }}
      animate={inView ? { opacity: 1, y: 0 } : undefined}
      transition={{ duration: 0.5, ease: "easeOut", delay }}
    >
      {children}
    </motion.div>
  );
}

function TerminalBlock() {
  const lines = [
    { prompt: "$", text: "pip install treco" },
    { prompt: "$", text: "treco init" },
    { prompt: "",  text: "✓ Agent registered  ·  workspace: my-project" },
    { prompt: "",  text: "✓ Claude Code hooks wired" },
    { prompt: "",  text: "✓ Dashboard at http://localhost:3000" },
    { prompt: "$", text: "treco start" },
    { prompt: "",  text: "◎ aurora  →  working on AUTH-42" },
  ];
  const [visible, setVisible] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (!inView) return;
    let i = 0;
    const id = setInterval(() => {
      i++;
      setVisible(i);
      if (i >= lines.length) clearInterval(id);
    }, 280);
    return () => clearInterval(id);
    // lines is stable — defined outside component
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView]);

  return (
    <div ref={ref} className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-5 font-mono text-sm overflow-x-auto">
      <div className="flex items-center gap-1.5 mb-4">
        <span className="w-3 h-3 rounded-full bg-[var(--red)]/60" />
        <span className="w-3 h-3 rounded-full bg-[var(--amber)]/60" />
        <span className="w-3 h-3 rounded-full bg-[var(--green)]/60" />
      </div>
      {lines.slice(0, visible).map((l, i) => (
        <div key={i} className="flex gap-3 leading-6">
          <span className="text-[var(--cyan)] select-none w-3">{l.prompt}</span>
          <span className={l.prompt ? "text-[var(--text)]" : "text-[var(--text-2)]"}>{l.text}</span>
        </div>
      ))}
      {visible < lines.length && (
        <div className="flex gap-3 leading-6">
          <span className="text-[var(--cyan)] select-none w-3">{lines[visible]?.prompt ?? ""}</span>
          <span className="inline-block w-2 h-4 bg-[var(--cyan)] animate-pulse" />
        </div>
      )}
    </div>
  );
}

const FEATURES = [
  {
    icon: "◎",
    title: "Live agent kanban",
    body: "Every agent visible: idle, working, errored. Left-edge indicator pulses while active. Updates in real time via SSE.",
  },
  {
    icon: "✓",
    title: "Criteria checklist",
    body: "Each ticket's acceptance criteria tick off as the agent completes them. Agent name and timestamp on every check.",
  },
  {
    icon: "◈",
    title: "Cost per session",
    body: "Tokens in, tokens out, estimated USD. Per-model breakdown, per-event bar chart. Know what every session costs.",
  },
  {
    icon: "≡",
    title: "Event feed",
    body: "Terminal-style log of every tool call, criterion check, and session event. Live-streamed. Searchable with Cmd+K.",
  },
];

const WORKS_WITH = ["Claude Code", "Cursor", "LangChain", "CrewAI", "AutoGen", "Any HTTP agent"];

export default function LandingPage() {
  const reduced = useReducedMotion();

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">

      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--bg)]/90 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <span className="text-[var(--cyan)] font-mono font-bold text-xl">⬡</span>
          <span className="font-bold text-lg tracking-tight">Treco</span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-sm text-[var(--text-2)] hover:text-[var(--text)] transition-colors">
            Dashboard
          </Link>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
            className="text-sm text-[var(--text-2)] hover:text-[var(--text)] transition-colors">
            GitHub
          </a>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium bg-[var(--cyan)] text-[var(--bg)] hover:opacity-90 transition-opacity">
            Get started free
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-36 pb-20 px-6 max-w-5xl mx-auto">
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--cyan)]/30 bg-[var(--cyan)]/10 text-[var(--cyan)] text-xs font-mono mb-8">
            <span className="relative flex h-1.5 w-1.5">
              <span className="ping-slow absolute inline-flex h-full w-full rounded-full bg-[var(--cyan)] opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[var(--cyan)]" />
            </span>
            open source · MIT
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.08] mb-6">
            See what your<br />
            <span className="text-[var(--cyan)]">AI agents</span> are doing.
          </h1>

          <p className="text-xl text-[var(--text-2)] max-w-2xl mb-10 leading-relaxed">
            Real-time observability for AI coding agents. Live kanban, acceptance criteria tracking,
            token cost per session. Two commands to start.
          </p>

          <div className="flex items-center gap-4 flex-wrap">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-lg px-6 py-3 text-base font-semibold bg-[var(--cyan)] text-[var(--bg)] hover:opacity-90 transition-opacity">
              Get started free →
            </a>
            <Link href="/dashboard"
              className="inline-flex items-center justify-center rounded-lg px-6 py-3 text-base font-medium border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--text)] transition-colors">
              View live demo
            </Link>
          </div>
        </motion.div>

        <FadeUp className="mt-16" delay={0.15}>
          <TerminalBlock />
        </FadeUp>
      </section>

      {/* Works with */}
      <FadeUp className="py-12 px-6 border-y border-[var(--border)]">
        <div className="max-w-5xl mx-auto">
          <p className="text-xs text-[var(--text-3)] font-mono uppercase tracking-widest mb-6 text-center">
            Works with
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {WORKS_WITH.map((name) => (
              <span key={name}
                className="px-4 py-2 rounded-full border border-[var(--border)] text-sm text-[var(--text-2)] font-mono bg-[var(--surface)]">
                {name}
              </span>
            ))}
          </div>
        </div>
      </FadeUp>

      {/* Features */}
      <section className="py-24 px-6 max-w-5xl mx-auto">
        <FadeUp>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Everything in one dashboard
          </h2>
          <p className="text-[var(--text-2)] text-lg max-w-xl mb-16">
            No polling. No manual status updates. Treco streams events directly from the agent session.
          </p>
        </FadeUp>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {FEATURES.map((f, i) => (
            <FadeUp key={f.title} delay={i * 0.07}>
              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 h-full">
                <span className="text-2xl text-[var(--cyan)] font-mono mb-4 block">{f.icon}</span>
                <h3 className="text-base font-semibold text-[var(--text)] mb-2">{f.title}</h3>
                <p className="text-sm text-[var(--text-2)] leading-relaxed">{f.body}</p>
              </div>
            </FadeUp>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 px-6 bg-[var(--surface)] border-y border-[var(--border)]">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-16 text-center">
              Two commands. Live in under a minute.
            </h2>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {[
              {
                n: "01",
                title: "Install and init",
                body: "pip install treco && treco init registers your agent, starts a local server, and wires Claude Code hooks automatically.",
                code: "pip install treco\ntreco init",
              },
              {
                n: "02",
                title: "Import a ticket",
                body: "Point Treco at a GitHub issue, Linear ticket, or Jira story. Acceptance criteria are extracted automatically.",
                code: "treco import \\\n  github.com/org/repo/issues/42",
              },
              {
                n: "03",
                title: "Run your agent",
                body: "Start Claude Code normally. Treco captures every tool call, token count, and criterion completion in real time.",
                code: "treco start\nclaude \"implement the issue\"",
              },
            ].map((s, i) => (
              <FadeUp key={s.n} delay={i * 0.1}>
                <div className="flex flex-col gap-4">
                  <span className="text-4xl font-bold text-[var(--cyan)] font-mono">{s.n}</span>
                  <h3 className="text-lg font-semibold">{s.title}</h3>
                  <p className="text-sm text-[var(--text-2)] leading-relaxed">{s.body}</p>
                  <pre className="mt-auto text-xs font-mono bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-3 text-[var(--cyan)] leading-5 whitespace-pre overflow-x-auto">{s.code}</pre>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* Dashboard screenshot */}
      <section className="py-24 px-6 max-w-5xl mx-auto">
        <FadeUp>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4 text-center">
            The whole picture, all at once
          </h2>
          <p className="text-[var(--text-2)] text-center mb-12 max-w-xl mx-auto">
            Agent kanban, live event feed, criteria burndown. One screen.
          </p>
        </FadeUp>
        <FadeUp delay={0.1}>
          <div className="rounded-xl border border-[var(--border)] overflow-hidden shadow-2xl">
            <img
              src="/dashboard-screenshot.png"
              alt="Treco dashboard — agent kanban, live event feed, criteria burndown"
              className="w-full block"
              width={1440}
              height={900}
            />
          </div>
        </FadeUp>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 border-t border-[var(--border)]">
        <FadeUp className="max-w-2xl mx-auto text-center">
          <span className="text-[var(--cyan)] text-3xl font-mono block mb-6">⬡</span>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Start observing your agents.
          </h2>
          <p className="text-[var(--text-2)] text-lg mb-10">
            Open source. MIT licensed. Self-host in two commands. No account required.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-lg px-8 py-3 text-base font-semibold bg-[var(--cyan)] text-[var(--bg)] hover:opacity-90 transition-opacity">
              Get started free →
            </a>
            <Link href="/dashboard"
              className="inline-flex items-center justify-center rounded-lg px-8 py-3 text-base font-medium border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--text)] transition-colors">
              View demo
            </Link>
          </div>
          <p className="text-xs text-[var(--text-3)] mt-8 font-mono">
            pip install treco · treco init · open localhost:3000
          </p>
        </FadeUp>
      </section>

      {/* Footer */}
      <footer className="py-10 px-6 border-t border-[var(--border)]">
        <div className="max-w-5xl mx-auto flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <span className="text-[var(--cyan)] font-mono">⬡</span>
            <span className="font-bold text-sm">Treco</span>
            <span className="text-[var(--text-3)] text-xs ml-1">— agent observability</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-[var(--text-3)]">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text)] transition-colors">GitHub</a>
            <Link href="/dashboard" className="hover:text-[var(--text)] transition-colors">Dashboard</Link>
            <span>MIT</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
