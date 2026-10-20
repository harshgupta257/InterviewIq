import type { ReactNode } from "react";

/** Numbered form section on the page grid: index + title + hint on the left, fields on the right. */
export function Step({ n, title, hint, children, aside }: { n: string; title: string; hint?: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="grid gap-5 border-t py-8 first:border-t-0 first:pt-0 md:grid-cols-[13rem_1fr] md:gap-10">
      <div>
        <p className="display text-3xl text-muted-foreground/60">{n}</p>
        <h2 className="mt-2 text-[15px] font-medium">{title}</h2>
        {hint && <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{hint}</p>}
        {aside}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}
