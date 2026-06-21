import Link from "next/link";
import { cn } from "@/lib/utils";
import { Bot, Ticket, Inbox, WifiOff, type LucideIcon } from "lucide-react";

interface EmptyStateProps {
  Icon?: LucideIcon;
  title: string;
  sub?: string;
  codeHint?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function EmptyState({ Icon, title, sub, codeHint, actions, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 text-center gap-2", className)}>
      {Icon && (
        <div aria-hidden="true" className="w-12 h-12 rounded-xl bg-[var(--green-3)] flex items-center justify-center mb-2">
          <Icon className="w-6 h-6 text-[var(--green)]" />
        </div>
      )}
      <p className="text-sm font-medium text-[var(--text-2)]">{title}</p>
      {sub && <p className="text-xs text-[var(--text-3)] max-w-xs">{sub}</p>}
      {codeHint && (
        <code className="code-chip mt-1">{codeHint}</code>
      )}
      {actions && <div className="flex gap-2 mt-3">{actions}</div>}
    </div>
  );
}

export function EmptyAgents() {
  return (
    <EmptyState
      Icon={Bot}
      title="No agents connected yet"
      sub="Run treco init in your project to connect this workspace."
      codeHint="treco init"
    />
  );
}

export function EmptyTickets({ onImport, onNew }: { onImport?: () => void; onNew?: () => void }) {
  return (
    <EmptyState
      Icon={Ticket}
      title="No tickets yet"
      sub="Import from GitHub, Linear, or Jira — or create one manually."
      actions={
        <>
          {onImport && (
            <button onClick={onImport} className="btn-secondary text-xs">
              Import tickets
            </button>
          )}
          {onNew && (
            <button onClick={onNew} className="btn-primary text-xs">
              New ticket
            </button>
          )}
        </>
      }
    />
  );
}

export function EmptyAgentIdle() {
  return (
    <EmptyState
      Icon={Inbox}
      title="Agent connected, waiting for a ticket"
      sub="Run treco start to assign a ticket to this agent."
      codeHint="treco start"
    />
  );
}

export function EmptyAgentNotFound() {
  return (
    <EmptyState
      Icon={Bot}
      title="Agent not found"
      sub="This agent may have been deleted or does not belong to this workspace."
      actions={
        <Link href="/agents" className="btn-secondary text-xs">
          ← Back to agents
        </Link>
      }
    />
  );
}

export function EmptyTicketFetchError() {
  return (
    <EmptyState
      Icon={WifiOff}
      title="Failed to load ticket"
      sub="There was a problem reaching the server. Check your connection and try again."
      actions={
        <button onClick={() => window.location.reload()} className="btn-secondary text-xs">
          Retry
        </button>
      }
    />
  );
}
