import { useQueryClient } from "@tanstack/react-query";
import type { Answer, SessionDetail } from "@/lib/types";
import { keys } from "./queries";

/** Replace one answer in the cached session so the UI updates without a refetch. */
export function useMergeAnswer(sessionId: string) {
  const qc = useQueryClient();
  return (answer: Answer) => {
    qc.setQueryData<SessionDetail>(keys.session(sessionId), (prev) => {
      if (!prev) return prev;
      const others = prev.answers.filter((a) => a.id !== answer.id && a.question_id !== answer.question_id);
      return { ...prev, answers: [...others, answer] };
    });
    // Aggregates (progress, status, dashboard, history) come from the server.
    void qc.invalidateQueries({ queryKey: keys.session(sessionId) });
    void qc.invalidateQueries({ queryKey: ["sessions"] });
    void qc.invalidateQueries({ queryKey: ["analytics"] });
  };
}
