"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useMemo } from "react";
import { useWorkspace } from "@/lib/workspace";
import { useAgents, useAgentEvents, useTickets } from "@/lib/hooks";
import { PulseRing } from "@/components/ui/PulseRing";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { TicketEventLog } from "@/components/ticket-detail/TicketEventLog";
import { EmptyAgentNotFound } from "@/components/ui/EmptyState";
import { estimateCost, formatCost, formatTokens } from "@/lib/cost";
import { toMap, toNameMap, sortChronological } from "@/lib/utils";
import type { LogPayload } from "@/lib/types";
import { getPayload } from "@/lib/types";

export function AgentDetailClient() {
  const { id } = useParams<{ id: string }>();
  const { workspaceId } = useWorkspace();

  const { data: agents = [], isLoading: agentsLoading } = useAgents(workspaceId);
  const { data: events = [], isLoading: eventsLoading } = useAgentEvents(id);
  const { data: tickets = [] } = useTickets(workspaceId);

  const agent = agents.find((a) => a.id === id);

  const agentNames = useMemo(() => toNameMap(agents), [agents]);
  const ticketMap = useMemo(() => toMap(tickets), [tickets]);

  const workedTicketIds = useMemo(() => {
    const ids = new Set<string>();
    events.forEach((ev) => ids.add(ev.ticket_id));
    return Array.from(ids);
  }, [events]);

  const totalTokensIn = events.reduce((s: number, ev) => s + ev.tokens_in, 0);
  const totalTokensOut = events.reduce((s: number, ev) => s + ev.tokens_out, 0);
  const totalCost = estimateCost(totalTokensIn, totalTokensOut, null);

  const chronologicalEvents = useMemo(() => sortChronological(events), [events]);

  const lastErrorMessage = useMemo(() => {
    const errorEvents = events.filter((ev) => ev.event_type === "error");
    const last = errorEvents[errorEvents.length - 1];
    return last ? (getPayload<LogPayload>(last).message ?? null) : null;
  }, [events]);

  if (agentsLoading || eventsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (!agent) {
    return <EmptyAgentNotFound />;
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/agents" className="text-text-muted hover:text-text-primary text-sm">← agents</Link>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3">
        <PulseRing active={agent.status === "working"} error={agent.status === "error"} />
        <h1 className="text-2xl font-bold text-text-primary">{agent.name}</h1>
        <Badge label={agent.status} />
      </div>

      {agent.status === "error" && (
        <div
          role="alert"
          className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3"
        >
          <span aria-hidden="true" className="text-red-500 mt-0.5">⚠</span>
          <div>
            <p className="text-sm font-medium text-red-600">Agent offline</p>
            <p className="text-xs text-text-muted mt-0.5">
              {lastErrorMessage ?? "Last run ended with an error. Restart the agent to resume work."}
            </p>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-surface border border-border-default rounded-xl p-4">
          <p className="text-xs text-text-muted mb-1">Total cost</p>
          <p className="text-lg font-bold text-text-primary">{formatCost(totalCost)}</p>
        </div>
        <div className="bg-surface border border-border-default rounded-xl p-4">
          <p className="text-xs text-text-muted mb-1">Tokens in / out</p>
          <p className="text-sm font-mono text-text-primary">
            {formatTokens(totalTokensIn)} / {formatTokens(totalTokensOut)}
          </p>
        </div>
        <div className="bg-surface border border-border-default rounded-xl p-4">
          <p className="text-xs text-text-muted mb-1">Tickets worked</p>
          <p className="text-lg font-bold text-text-primary">{workedTicketIds.length}</p>
        </div>
      </div>

      {/* Tickets worked */}
      {workedTicketIds.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-text-primary mb-3">Tickets</h2>
          <div className="flex flex-col gap-2">
            {workedTicketIds.map((tid) => {
              const t = ticketMap[tid];
              return (
                <Link
                  key={tid}
                  href={`/tickets/${tid}`}
                  className="bg-surface border border-border-default rounded-lg px-4 py-2.5 flex items-center gap-3 hover:border-green-brand/30 transition-colors"
                >
                  <span className="text-xs font-mono text-text-muted">{t?.source_id ?? tid.slice(0, 8)}</span>
                  <span className="text-sm text-text-primary truncate">{t?.title ?? tid}</span>
                  {t && <Badge label={t.status} />}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Event log */}
      <div>
        <h2 className="text-sm font-semibold text-text-primary mb-3">
          Event history
          <span className="ml-2 text-text-muted font-normal">{events.length} events</span>
        </h2>
        <div style={{ height: 400 }}>
          <TicketEventLog events={chronologicalEvents} agents={agents} />
        </div>
      </div>
    </div>
  );
}
