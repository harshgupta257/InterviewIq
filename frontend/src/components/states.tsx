import { AlertTriangle, Loader2, RefreshCw, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";

export function FullPageLoader({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <Loader2 className="size-5 animate-spin text-muted-foreground" aria-hidden />
      <span className="ml-2 text-sm text-muted-foreground">{label}…</span>
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  title,
  className,
  action,
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
  className?: string;
  action?: ReactNode;
}) {
  const network = error instanceof ApiError && error.isNetwork;
  const notFound = error instanceof ApiError && error.status === 404;
  const Icon = network ? WifiOff : AlertTriangle;
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-12 text-center", className)} role="alert">
      <div className="border border-destructive p-2.5 text-destructive">
        <Icon className="size-5" aria-hidden />
      </div>
      <div className="space-y-1">
        <p className="font-medium">{title ?? (network ? "You appear to be offline" : notFound ? "Not found" : "Something went wrong")}</p>
        <p className="max-w-md text-sm text-muted-foreground">{errorMessage(error)}</p>
        {error instanceof ApiError && error.requestId && (
          <p className="text-xs text-muted-foreground">Reference: {error.requestId}</p>
        )}
      </div>
      <div className="flex gap-2">
        {onRetry && !notFound && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw /> Try again
          </Button>
        )}
        {action}
      </div>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-12 text-center", className)}>
      {icon && <div className="border border-foreground p-2.5 text-foreground [&_svg]:size-5">{icon}</div>}
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        {description && <p className="mx-auto max-w-md text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
