import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PenLine } from "lucide-react";
import { toast } from "sonner";
import { keys } from "@/hooks/queries";
import { api, ApiError, errorMessage } from "@/lib/api";
import { useMergeAnswer } from "@/hooks/useMergeAnswer";
import type { Answer } from "@/lib/types";
import { EvaluatingState, EvaluationFailed, EvaluationPanel, RewritePanel } from "./evaluation";
import { Button } from "./ui/button";
import { Alert } from "./ui/primitives";

export function AnswerReview({ answer, sessionId }: { answer: Answer; sessionId: string }) {
  const merge = useMergeAnswer(sessionId);
  const qc = useQueryClient();

  const retry = useMutation({
    mutationFn: () => api.retryEvaluation(answer.id),
    onSuccess: (a) => {
      merge(a);
      if (a.evaluation_status === "completed") toast.success("Evaluation complete");
      else if (a.evaluation_status === "failed") toast.error("Evaluation failed again. Please try later.");
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) void qc.invalidateQueries({ queryKey: keys.session(sessionId) });
      toast.error(errorMessage(err));
    },
  });

  const rewrite = useMutation({
    mutationFn: (regenerate: boolean) => api.rewrite(answer.id, regenerate),
    onSuccess: merge,
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div className="space-y-4">
      {answer.evaluation_status === "completed" && answer.evaluation && <EvaluationPanel evaluation={answer.evaluation} />}
      {answer.evaluation_status === "failed" && (
        <EvaluationFailed answer={answer} onRetry={() => retry.mutate()} retrying={retry.isPending} />
      )}
      {(answer.evaluation_status === "pending" || answer.evaluation_status === "evaluating") && <EvaluatingState />}

      {answer.rewrite ? (
        <RewritePanel
          original={answer.answer_text}
          rewrite={answer.rewrite}
          onRegenerate={() => rewrite.mutate(true)}
          regenerating={rewrite.isPending}
        />
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" onClick={() => rewrite.mutate(false)} loading={rewrite.isPending}>
            {!rewrite.isPending && <PenLine />}
            {rewrite.isPending ? "Writing an example…" : "Show a stronger answer"}
          </Button>
          {rewrite.isError && (
            <Alert tone="error" className="py-2">
              {errorMessage(rewrite.error)}
            </Alert>
          )}
        </div>
      )}
    </div>
  );
}
