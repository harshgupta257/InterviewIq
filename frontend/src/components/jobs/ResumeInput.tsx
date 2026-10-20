import { useMutation } from "@tanstack/react-query";
import { FileUp, History, Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, FieldError, Label, Textarea } from "@/components/ui/primitives";
import { useConfig, useSessions } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCEPT = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/** Resume source: upload (PDF/DOCX), paste, or reuse the resume from the latest interview. */
export function ResumeInput({ value, onChange, error }: { value: string; onChange: (text: string) => void; error?: string }) {
  const config = useConfig();
  const maxMb = config.data?.job_search.upload_max_mb ?? 5;
  const max = config.data?.limits.resume_max ?? 15000;
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [fileInfo, setFileInfo] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const latest = useSessions({ page: 1, page_size: 1, sort: "date_desc" });
  const latestId = latest.data?.items[0]?.id;

  const upload = useMutation({
    mutationFn: (file: File) => {
      if (file.size > maxMb * 1024 * 1024) throw new Error(`The file is larger than ${maxMb} MB.`);
      if (!/\.(pdf|docx)$/i.test(file.name)) throw new Error("Upload a PDF or DOCX file, or paste your resume as text.");
      return api.extractResume(file);
    },
    onSuccess: (res, file) => {
      onChange(res.text);
      setWarnings(res.warnings);
      setFileInfo(`${file.name} · ${res.file_type.toUpperCase()}${res.pages ? ` · ${res.pages} page${res.pages > 1 ? "s" : ""}` : ""} · ${res.char_count.toLocaleString()} characters extracted`);
    },
    onError: () => setFileInfo(null),
  });

  const reuse = useMutation({
    mutationFn: async () => (await api.getSession(latestId!)).resume_text,
    onSuccess: (text) => {
      onChange(text);
      setWarnings([]);
      setFileInfo("Resume reused from your latest interview");
    },
  });

  const pick = (files: FileList | null) => {
    const f = files?.[0];
    if (f) upload.mutate(f);
  };

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files);
        }}
        className={cn(
          "flex flex-col gap-4 border border-dashed border-foreground p-6 transition-all duration-200 sm:flex-row sm:items-center sm:justify-between",
          dragging && "bg-secondary",
        )}
      >
        <div className="flex items-start gap-4">
          {upload.isPending ? <Loader2 className="mt-0.5 size-5 shrink-0 animate-spin" aria-hidden /> : <FileUp className="mt-0.5 size-5 shrink-0" strokeWidth={1.5} aria-hidden />}
          <div>
            <p className="text-[15px] font-semibold">{upload.isPending ? "Reading your resume…" : "Upload your resume"}</p>
            <p className="text-sm text-muted-foreground">PDF or DOCX, up to {maxMb} MB. Drop it here or choose a file.</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <input ref={fileRef} type="file" accept={ACCEPT} className="sr-only" id="resume-file" onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
          <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={upload.isPending}>
            Choose file
          </Button>
          {latestId && (
            <Button type="button" variant="ghost" size="sm" onClick={() => reuse.mutate()} loading={reuse.isPending}>
              {!reuse.isPending && <History />} Use latest resume
            </Button>
          )}
        </div>
      </div>

      <div aria-live="polite" className="space-y-2">
        {fileInfo && <p className="text-sm font-medium">{fileInfo}</p>}
        {upload.isError && (
          <Alert tone="error" title="We couldn't use that file">
            {errorMessage(upload.error)}
          </Alert>
        )}
        {reuse.isError && <Alert tone="error">{errorMessage(reuse.error)}</Alert>}
        {warnings.map((w) => (
          <Alert key={w} tone="warning">
            {w}
          </Alert>
        ))}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="jf-resume">Resume text — review or paste</Label>
          <span className={cn("text-xs tabular-nums", value.length > max ? "text-destructive" : "text-muted-foreground")}>
            {value.length.toLocaleString()} / {max.toLocaleString()}
          </span>
        </div>
        <Textarea
          id="jf-resume"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="min-h-[200px] text-[14px]"
          placeholder="Extracted text appears here. You can also paste your resume directly."
          aria-invalid={!!error}
          aria-describedby="jf-resume-error jf-resume-note"
        />
        <FieldError id="jf-resume-error" message={error} />
        <p id="jf-resume-note" className="text-xs text-muted-foreground">
          Kept in this browser tab only. Contact details are removed before analysis; only role keywords and your location are
          sent to the job-search service.
        </p>
      </div>
    </div>
  );
}
