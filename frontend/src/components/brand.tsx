import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

/** Geometric mark: a bar, a beam and an accent dot on a square. */
export function Mark({ className, inverse = false }: { className?: string; inverse?: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-7 shrink-0", className)} aria-hidden>
      <rect width="32" height="32" fill={inverse ? "#FFFFFF" : "currentColor"} />
      <circle cx="22" cy="10" r="5" fill="#B38B6D" />
      <rect x="7" y="7" width="4" height="18" fill={inverse ? "#000000" : "hsl(var(--background))"} />
      <rect x="14" y="17" width="11" height="4" fill={inverse ? "#000000" : "hsl(var(--background))"} />
    </svg>
  );
}

export function Wordmark({ className, light = false, to = "/" }: { className?: string; light?: boolean; to?: string }) {
  return (
    <Link
      to={to}
      className={cn("inline-flex items-center gap-2.5 transition-opacity duration-200 hover:opacity-80", light ? "text-paper" : "text-foreground", className)}
      aria-label="InterviewIQ home"
    >
      <Mark inverse={light} />
      <span className="text-[15px] font-bold tracking-[-0.02em]">InterviewIQ</span>
    </Link>
  );
}

/**
 * Abstract hero visual built only from flat geometry on a 6x6 grid:
 * squares, a circle, a quarter disc and rules. No gradients, no shadows.
 * The ring rotates slowly; the motion is disabled for reduced-motion users.
 */
export function SwissComposition({ className }: { className?: string }) {
  return (
    <div className={cn("relative aspect-square w-full select-none", className)} aria-hidden>
      <svg viewBox="0 0 600 600" className="absolute inset-0 h-full w-full">
        {/* grid */}
        <g stroke="currentColor" strokeOpacity="0.14" strokeWidth="1">
          {[100, 200, 300, 400, 500].map((v) => (
            <g key={v}>
              <line x1={v} y1="0" x2={v} y2="600" />
              <line x1="0" y1={v} x2="600" y2={v} />
            </g>
          ))}
        </g>
        {/* large black field */}
        <rect x="0" y="200" width="400" height="400" fill="currentColor" />
        {/* beige square */}
        <rect x="300" y="0" width="300" height="300" fill="#F5F1E8" />
        {/* taupe circle, the single accent */}
        <circle cx="450" cy="150" r="110" fill="#B38B6D" />
        {/* quarter disc cut from the black field */}
        <path d="M0 600 V400 A200 200 0 0 1 200 600 Z" fill="#F5F1E8" />
        {/* white bars inside black field: 8 questions */}
        <g fill="#FFFFFF">
          {Array.from({ length: 8 }).map((_, i) => (
            <rect key={i} x={240 + (i % 4) * 34} y={240 + Math.floor(i / 4) * 60} width="22" height={i === 2 ? 44 : 22} />
          ))}
        </g>
        {/* rules */}
        <line x1="0" y1="200" x2="600" y2="200" stroke="currentColor" strokeWidth="2" />
        <line x1="400" y1="200" x2="400" y2="600" stroke="currentColor" strokeWidth="2" />
        <text x="420" y="580" fill="currentColor" fontFamily="Archivo, Helvetica, Arial, sans-serif" fontSize="132" fontWeight="700" letterSpacing="-8">
          08
        </text>
      </svg>
      <svg viewBox="0 0 600 600" className="absolute inset-0 h-full w-full motion-safe:animate-spin-slow" style={{ transformOrigin: "75% 25%" }}>
        <circle cx="450" cy="150" r="140" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 10" />
      </svg>
    </div>
  );
}
