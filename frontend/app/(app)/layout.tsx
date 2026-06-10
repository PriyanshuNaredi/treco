import { WorkspaceProvider } from "@/lib/workspace";
import { StreamProvider } from "@/lib/StreamProvider";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { CommandPaletteProvider } from "@/components/ui/CommandPaletteProvider";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <StreamProvider>
        <CommandPaletteProvider />
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </StreamProvider>
    </WorkspaceProvider>
  );
}
