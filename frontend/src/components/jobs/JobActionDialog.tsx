import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Alert, Label, Select, Textarea } from "@/components/ui/primitives";
import { ROLE_OPTIONS } from "@/lib/constants";
import { guessRoleType } from "@/lib/jobs";
import type { JobResult, RoleType } from "@/lib/types";

const MIN = 100;

/**
 * Two uses:
 *  - "prepare": choose the interview role category and confirm or replace the job description.
 *  - "rescore": paste the full job description to re-evaluate the match.
 */
export function JobActionDialog({
  job,
  mode,
  open,
  onOpenChange,
  onSubmit,
  pending,
  error,
  needsResume,
}: {
  job: JobResult | null;
  mode: "prepare" | "rescore";
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onSubmit: (v: { role_type: RoleType; description: string; descriptionChanged: boolean }) => void;
  pending: boolean;
  error: string | null;
  needsResume: boolean;
}) {
  const [role, setRole] = useState<RoleType>("software_engineering");
  const [desc, setDesc] = useState("");

  useEffect(() => {
    if (job && open) {
      setRole(guessRoleType(job.title));
      setDesc(mode === "rescore" && job.description_source === "listing_summary" ? "" : job.description ?? "");
    }
  }, [job, open, mode]);

  if (!job) return null;
  const original = job.description ?? "";
  const tooShort = desc.trim().length < MIN;
  const isSummary = job.description_source === "listing_summary";

  return (
    <Dialog open={open} onOpenChange={(o) => !pending && onOpenChange(o)}>
      <DialogContent className="max-w-2xl">
        <div className="space-y-2">
          <DialogTitle className="text-xl font-bold tracking-[-0.02em]">
            {mode === "prepare" ? "Prepare for this interview" : "Re-score with the full description"}
          </DialogTitle>
          <DialogDescription>
            {job.title}
            {job.company ? ` · ${job.company}` : ""}
          </DialogDescription>
        </div>

        {needsResume && (
          <Alert tone="error" title="Your resume is needed">
            Add your resume in step 01 on this page first. It isn't stored between visits.
          </Alert>
        )}

        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            if (!tooShort && !needsResume) onSubmit({ role_type: role, description: desc.trim(), descriptionChanged: desc.trim() !== original.trim() });
          }}
        >
          {mode === "prepare" && (
            <div className="space-y-2">
              <Label htmlFor="jd-role">Interview role category</Label>
              <Select id="jd-role" value={role} onChange={(e) => setRole(e.target.value as RoleType)}>
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="jd-text">Job description</Label>
            {isSummary && (
              <p className="text-sm text-muted-foreground">
                Listing summaries are short. For {mode === "prepare" ? "better questions" : "a full evaluation"}, open the job
                page, copy the complete description and paste it here.
              </p>
            )}
            <Textarea
              id="jd-text"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="min-h-[220px] text-[14px]"
              placeholder="Paste the full job description from the listing page."
              aria-invalid={tooShort && desc.length > 0}
            />
            <p className="text-xs tabular-nums text-muted-foreground">
              {desc.trim().length.toLocaleString()} characters{tooShort ? ` · at least ${MIN} needed` : ""}
            </p>
          </div>
          {error && <Alert tone="error">{error}</Alert>}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)} disabled={pending}>
              Cancel
            </Button>
            <Button type="submit" loading={pending} disabled={tooShort || needsResume}>
              {mode === "prepare" ? (pending ? "Generating questions…" : "Generate interview") : pending ? "Re-scoring…" : "Re-score"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
