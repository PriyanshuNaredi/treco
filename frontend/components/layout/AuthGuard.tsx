"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getValidToken } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    getValidToken().then((token) => {
      if (!token) {
        router.replace("/login");
      } else {
        setReady(true);
      }
    });
  }, [router]);

  if (!ready) {
    return (
      <div className="min-h-screen bg-[var(--bg)] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-[var(--green)] border-t-transparent animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
