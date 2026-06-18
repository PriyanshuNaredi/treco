"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useWorkspace } from "@/lib/workspace";
import { useAgents } from "@/lib/hooks";
import type { Workspace } from "@/lib/types";
import { NewWorkspaceModal } from "./NewWorkspaceModal";

function WorkspaceTab({ workspace, active, onClick }: { workspace: Workspace; active: boolean; onClick: () => void }) {
  const { data: agents } = useAgents(workspace.id);
  const working = agents?.filter((a) => a.status === "working").length ?? 0;

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs border transition-colors ${
        active
          ? "bg-[var(--green-3)] border-[var(--green)]/40 text-[var(--green)] font-medium"
          : "border-[var(--border)] text-[var(--text-2)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]"
      }`}
    >
      {workspace.name}
      {working > 0 && (
        <span className="flex items-center justify-center min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-[var(--green)]/15 text-[var(--green)] text-[10px] font-semibold">
          {working}
        </span>
      )}
    </button>
  );
}

export function WorkspaceTabs() {
  const { workspaceId, setWorkspaceId, workspaces } = useWorkspace();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="flex items-center gap-2">
      {workspaces.map((w) => (
        <WorkspaceTab
          key={w.id}
          workspace={w}
          active={w.id === workspaceId}
          onClick={() => setWorkspaceId(w.id)}
        />
      ))}
      <button
        onClick={() => setModalOpen(true)}
        aria-label="New workspace"
        className="flex items-center justify-center w-7 h-7 rounded-lg border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--text)] hover:bg-[var(--surface-2)] transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
      </button>
      {modalOpen && <NewWorkspaceModal onClose={() => setModalOpen(false)} />}
    </div>
  );
}
