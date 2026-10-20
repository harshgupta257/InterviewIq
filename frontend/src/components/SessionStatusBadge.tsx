import { CheckCircle2, CircleDashed, XCircle } from "lucide-react";
import { Badge } from "./ui/primitives";

export function SessionStatusBadge({ status }: { status: string }) {
  if (status === "completed")
    return (
      <Badge tone="success">
        <CheckCircle2 aria-hidden /> Completed
      </Badge>
    );
  if (status === "failed")
    return (
      <Badge tone="destructive">
        <XCircle aria-hidden /> Failed
      </Badge>
    );
  return (
    <Badge tone="primary">
      <CircleDashed aria-hidden /> In progress
    </Badge>
  );
}
