import { useState, type ReactNode } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { Alert, Input, Label } from "./ui/primitives";

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  onConfirm,
  pending,
  error,
  requireText,
}: {
  open: boolean;
  onOpenChange(open: boolean): void;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  onConfirm(): void;
  pending?: boolean;
  error?: string | null;
  /** If set, the user must type this exact text to enable the confirm button. */
  requireText?: string;
}) {
  const [typed, setTyped] = useState("");
  const blocked = requireText ? typed !== requireText : false;
  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!pending) {
          setTyped("");
          onOpenChange(o);
        }
      }}
    >
      <DialogContent>
        <div className="space-y-2">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription asChild>
            <div>{description}</div>
          </DialogDescription>
        </div>
        {requireText && (
          <div className="space-y-1.5">
            <Label htmlFor="confirm-text">
              Type <span className="font-mono font-semibold">{requireText}</span> to confirm
            </Label>
            <Input id="confirm-text" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          </div>
        )}
        {error && <Alert tone="error">{error}</Alert>}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} loading={pending} disabled={blocked}>
            {confirmLabel}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
