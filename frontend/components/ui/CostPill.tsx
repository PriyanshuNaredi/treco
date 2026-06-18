import { estimateCost, formatCost } from "@/lib/cost";

interface CostPillProps {
  tokensIn: number;
  tokensOut: number;
  model?: string | null;
}

export function CostPill({ tokensIn, tokensOut, model }: CostPillProps) {
  const usd = estimateCost(tokensIn, tokensOut, model ?? null);
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-violet-50 border border-violet-200 text-violet-600 font-mono">
      {formatCost(usd)}
    </span>
  );
}
