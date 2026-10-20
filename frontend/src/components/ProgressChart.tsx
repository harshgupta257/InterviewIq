import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipProps } from "recharts";
import type { ProgressPoint } from "@/lib/types";
import { formatDate, formatPct } from "@/lib/utils";
import { Button } from "./ui/button";

const LINE = "hsl(var(--chart-line))";
const GRID = "hsl(var(--chart-grid))";
const AXIS = "hsl(var(--muted-foreground))";

function ChartTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload as ProgressPoint & { label: string };
  return (
    <div className="border border-foreground bg-popover px-3 py-2 text-xs">
      <p className="font-medium text-foreground">{p.job_title}{p.company ? ` · ${p.company}` : ""}</p>
      <p className="text-muted-foreground">{formatDate(p.date)}</p>
      <p className="mt-1 text-foreground">
        <span className="font-semibold tabular-nums">{formatPct(p.average_score, 1)}</span>
        <span className="text-muted-foreground"> average · {p.evaluated_count} answers{p.is_demo ? " · sample data" : ""}</span>
      </p>
    </div>
  );
}

/** Single-series trend of session average scores. One hue, no legend (the title names it). */
export function ProgressChart({ points }: { points: ProgressPoint[] }) {
  const [asTable, setAsTable] = useState(false);
  const data = points.map((p) => ({ ...p, label: formatDate(p.date, { month: "short", day: "numeric" }) }));
  const last = data[data.length - 1];

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button variant="ghost" size="sm" onClick={() => setAsTable((t) => !t)} aria-pressed={asTable}>
          {asTable ? "Show chart" : "Show as table"}
        </Button>
      </div>
      {asTable ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Average score per session</caption>
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Date</th>
                <th className="py-2 pr-4 font-medium">Session</th>
                <th className="py-2 pr-4 text-right font-medium">Answers</th>
                <th className="py-2 text-right font-medium">Average</th>
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.session_id} className="border-b last:border-0">
                  <td className="py-2 pr-4 text-muted-foreground">{formatDate(p.date)}</td>
                  <td className="py-2 pr-4">{p.job_title}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{p.evaluated_count}</td>
                  <td className="py-2 text-right font-medium tabular-nums">{formatPct(p.average_score, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-64 w-full" role="img" aria-label={`Average score trend across ${data.length} sessions; latest ${formatPct(last?.average_score)}`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 16, right: 40, bottom: 0, left: -12 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: AXIS, fontSize: 12 }} tickMargin={8} minTickGap={16} />
              <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickLine={false} axisLine={false} tick={{ fill: AXIS, fontSize: 12 }} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: AXIS, strokeWidth: 1, strokeDasharray: "3 3" }} />
              <Line
                type="monotone"
                dataKey="average_score"
                stroke={LINE}
                strokeWidth={2}
                dot={{ r: 4, fill: LINE, stroke: "hsl(var(--card))", strokeWidth: 2 }}
                activeDot={{ r: 6, fill: LINE, stroke: "hsl(var(--card))", strokeWidth: 2 }}
                isAnimationActive={false}
                label={(props: { x?: number; y?: number; index?: number }) =>
                  props.index === data.length - 1 ? (
                    <text x={(props.x ?? 0) + 10} y={(props.y ?? 0) + 4} fontSize={12} fontWeight={600} fill="hsl(var(--foreground))">
                      {formatPct(last.average_score)}
                    </text>
                  ) : (
                    <g />
                  )
                }
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
