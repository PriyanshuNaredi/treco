"use client";

import { useState } from "react";
import Link from "next/link";
import { useWorkspace } from "@/lib/workspace";
import { fetchGitHubIssues, fetchLinearIssues, importTicket } from "@/lib/api";
import type { Ticket } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";

type ImportSource = "github" | "linear" | "paste";

interface SourceCard {
  value: ImportSource;
  label: string;
  description: string;
}

const SOURCES: SourceCard[] = [
  { value: "github", label: "GitHub Issues", description: "Import via Personal Access Token" },
  { value: "linear", label: "Linear", description: "Import via API key" },
  { value: "paste", label: "Paste URL", description: "Paste any issue URL" },
];

interface FetchedIssue {
  ticket: Ticket;
  selected: boolean;
}

type Step = 1 | 2 | 3;

export default function ImportPage() {
  const { workspaceId } = useWorkspace();

  const [step, setStep] = useState<Step>(1);
  const [source, setSource] = useState<ImportSource | null>(null);

  // Step 2 state — GitHub
  const [ghToken, setGhToken] = useState("");
  const [ghRepo, setGhRepo] = useState("");

  // Step 2 state — Linear
  const [linearKey, setLinearKey] = useState("");
  const [linearTeam, setLinearTeam] = useState("");

  // Step 2 state — Paste URL
  const [pasteUrl, setPasteUrl] = useState("");

  const [fetchError, setFetchError] = useState("");
  const [fetching, setFetching] = useState(false);

  // Step 3 state
  const [issues, setIssues] = useState<FetchedIssue[]>([]);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importedCount, setImportedCount] = useState<number | null>(null);
  const [importError, setImportError] = useState("");

  function selectSource(s: ImportSource) {
    setSource(s);
    setStep(2);
    setFetchError("");
  }

  async function handleFetch() {
    if (!source) return;
    setFetchError("");
    setFetching(true);

    try {
      let tickets: Ticket[] = [];

      if (source === "github") {
        if (!ghToken.trim() || !ghRepo.trim()) {
          setFetchError("Token and repository are required");
          setFetching(false);
          return;
        }
        tickets = await fetchGitHubIssues(workspaceId, ghRepo.trim(), ghToken.trim());
      } else if (source === "linear") {
        if (!linearKey.trim()) {
          setFetchError("API key is required");
          setFetching(false);
          return;
        }
        tickets = await fetchLinearIssues(workspaceId, linearTeam.trim(), linearKey.trim());
      } else if (source === "paste") {
        if (!pasteUrl.trim()) {
          setFetchError("URL is required");
          setFetching(false);
          return;
        }
        const res = await fetch("/api/tickets/fetch/url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ workspace_id: workspaceId, url: pasteUrl.trim() }),
        });
        if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
        const ticket = await res.json() as Ticket;
        tickets = [ticket];
      }

      setIssues(tickets.map((t) => ({ ticket: t, selected: true })));
      setStep(3);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Failed to fetch issues");
    } finally {
      setFetching(false);
    }
  }

  function toggleIssue(index: number) {
    setIssues((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, selected: !item.selected } : item
      )
    );
  }

  function toggleAll() {
    const allSelected = issues.every((i) => i.selected);
    setIssues((prev) => prev.map((item) => ({ ...item, selected: !allSelected })));
  }

  async function handleImport() {
    const selected = issues.filter((i) => i.selected);
    if (selected.length === 0) return;

    setImporting(true);
    setImportError("");
    setImportProgress(0);

    let done = 0;
    try {
      for (const item of selected) {
        await importTicket({
          workspace_id: workspaceId,
          title: item.ticket.title,
          description: item.ticket.description ?? undefined,
          source_id: item.ticket.source_id ?? undefined,
          source: item.ticket.source,
        });
        done++;
        setImportProgress(Math.round((done / selected.length) * 100));
      }
      setImportedCount(done);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  const selectedCount = issues.filter((i) => i.selected).length;

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => {
            if (step > 1) setStep((step - 1) as Step);
          }}
          className="text-text-muted hover:text-text-primary transition-colors text-sm"
        >
          ← Back
        </button>
        <h1 className="text-xl font-bold text-text-primary">Import Tickets</h1>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {([1, 2, 3] as Step[]).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border transition-colors ${
                step === s
                  ? "bg-cyan-brand border-cyan-brand text-bg"
                  : step > s
                  ? "bg-green-brand/20 border-green-brand text-green-brand"
                  : "bg-surface border-border-default text-text-muted"
              }`}
            >
              {step > s ? "✓" : s}
            </div>
            <span
              className={`text-sm ${
                step === s ? "text-text-primary font-medium" : "text-text-muted"
              }`}
            >
              {s === 1 ? "Choose source" : s === 2 ? "Connect" : "Select & import"}
            </span>
            {s < 3 && <span className="text-border-default mx-1">—</span>}
          </div>
        ))}
      </div>

      {/* Step 1: Choose source */}
      {step === 1 && (
        <div className="grid grid-cols-2 gap-4">
          {SOURCES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => selectSource(s.value)}
              className="flex flex-col gap-2 p-5 bg-surface border border-border-default rounded-xl text-left hover:border-cyan-brand transition-colors group"
            >
              <span className="text-2xl text-cyan-brand group-hover:scale-110 transition-transform">
                ◈
              </span>
              <p className="font-semibold text-text-primary">{s.label}</p>
              <p className="text-sm text-text-muted">{s.description}</p>
            </button>
          ))}
          {/* Jira card — disabled placeholder for future */}
          <button
            type="button"
            disabled
            className="flex flex-col gap-2 p-5 bg-surface border border-border-default rounded-xl text-left opacity-40 cursor-not-allowed"
          >
            <span className="text-2xl text-text-muted">◈</span>
            <p className="font-semibold text-text-primary">Jira</p>
            <p className="text-sm text-text-muted">Import via API token + domain</p>
          </button>
          <button
            type="button"
            disabled
            className="flex flex-col gap-2 p-5 bg-surface border border-border-default rounded-xl text-left opacity-40 cursor-not-allowed"
          >
            <span className="text-2xl text-text-muted">◈</span>
            <p className="font-semibold text-text-primary">Asana</p>
            <p className="text-sm text-text-muted">Import via Personal Access Token</p>
          </button>
        </div>
      )}

      {/* Step 2: Connect */}
      {step === 2 && source && (
        <Card className="flex flex-col gap-5">
          {source === "github" && (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-text-primary" htmlFor="gh-token">
                  Personal Access Token
                </label>
                <input
                  id="gh-token"
                  type="password"
                  value={ghToken}
                  onChange={(e) => setGhToken(e.target.value)}
                  placeholder="ghp_…"
                  className="bg-bg border border-border-default rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-cyan-brand transition-colors font-mono"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-text-primary" htmlFor="gh-repo">
                  Repository
                </label>
                <input
                  id="gh-repo"
                  type="text"
                  value={ghRepo}
                  onChange={(e) => setGhRepo(e.target.value)}
                  placeholder="owner/repo"
                  className="bg-bg border border-border-default rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-cyan-brand transition-colors font-mono"
                />
              </div>
            </>
          )}

          {source === "linear" && (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-text-primary" htmlFor="linear-key">
                  API Key
                </label>
                <input
                  id="linear-key"
                  type="password"
                  value={linearKey}
                  onChange={(e) => setLinearKey(e.target.value)}
                  placeholder="lin_api_…"
                  className="bg-bg border border-border-default rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-cyan-brand transition-colors font-mono"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-text-primary" htmlFor="linear-team">
                  Team Key{" "}
                  <span className="text-text-muted font-normal">(optional)</span>
                </label>
                <input
                  id="linear-team"
                  type="text"
                  value={linearTeam}
                  onChange={(e) => setLinearTeam(e.target.value)}
                  placeholder="ENG"
                  className="bg-bg border border-border-default rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-cyan-brand transition-colors font-mono"
                />
              </div>
            </>
          )}

          {source === "paste" && (
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-primary" htmlFor="paste-url">
                Issue URL
              </label>
              <textarea
                id="paste-url"
                value={pasteUrl}
                onChange={(e) => setPasteUrl(e.target.value)}
                placeholder="https://github.com/owner/repo/issues/123"
                rows={3}
                className="bg-bg border border-border-default rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-cyan-brand transition-colors resize-none font-mono"
              />
            </div>
          )}

          {fetchError && (
            <p className="text-sm text-red-brand bg-red-brand/10 border border-red-brand/20 rounded-lg px-3 py-2">
              {fetchError}
            </p>
          )}

          <button
            type="button"
            onClick={handleFetch}
            disabled={fetching}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-cyan-brand text-bg font-semibold rounded-lg hover:bg-cyan-brand/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {fetching && <Spinner className="border-bg border-r-transparent" />}
            {fetching ? "Fetching…" : "Fetch Issues"}
          </button>
        </Card>
      )}

      {/* Step 3: Select & import */}
      {step === 3 && (
        <div className="flex flex-col gap-4">
          {importedCount !== null ? (
            <Card className="flex flex-col items-center gap-4 py-8">
              <span className="text-4xl text-green-brand">✓</span>
              <p className="text-lg font-semibold text-text-primary">
                Imported {importedCount} ticket{importedCount !== 1 ? "s" : ""}
              </p>
              <Link
                href="/tickets"
                className="px-5 py-2 bg-cyan-brand text-bg font-semibold rounded-lg hover:bg-cyan-brand/90 transition-colors"
              >
                View tickets →
              </Link>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">
                  {issues.length} issue{issues.length !== 1 ? "s" : ""} found
                </p>
                <button
                  type="button"
                  onClick={toggleAll}
                  className="text-xs text-cyan-brand hover:underline"
                >
                  {issues.every((i) => i.selected) ? "Deselect all" : "Select all"}
                </button>
              </div>

              <Card className="p-0 overflow-hidden">
                <ul className="divide-y divide-border-default">
                  {issues.map((item, index) => (
                    <li
                      key={item.ticket.id}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-surface-2 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={item.selected}
                        onChange={() => toggleIssue(index)}
                        className="w-4 h-4 accent-cyan-brand flex-shrink-0"
                        id={`issue-${index}`}
                      />
                      <label
                        htmlFor={`issue-${index}`}
                        className="flex-1 flex items-center gap-3 cursor-pointer min-w-0"
                      >
                        {item.ticket.source_id && (
                          <span className="text-xs text-text-muted font-mono flex-shrink-0">
                            #{item.ticket.source_id}
                          </span>
                        )}
                        <span className="text-sm text-text-primary truncate">
                          {item.ticket.title}
                        </span>
                      </label>
                      <Badge label={item.ticket.status} />
                    </li>
                  ))}
                </ul>
              </Card>

              {importing && (
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs text-text-muted">
                    <span>Importing…</span>
                    <span>{importProgress}%</span>
                  </div>
                  <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan-brand transition-all duration-300"
                      style={{ width: `${importProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {importError && (
                <p className="text-sm text-red-brand bg-red-brand/10 border border-red-brand/20 rounded-lg px-3 py-2">
                  {importError}
                </p>
              )}

              <button
                type="button"
                onClick={handleImport}
                disabled={importing || selectedCount === 0}
                className="flex items-center justify-center gap-2 px-5 py-2.5 bg-cyan-brand text-bg font-semibold rounded-lg hover:bg-cyan-brand/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importing && <Spinner className="border-bg border-r-transparent" />}
                {importing
                  ? "Importing…"
                  : `Import Selected (${selectedCount})`}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
