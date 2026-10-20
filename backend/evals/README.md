# Evaluator agreement pipeline

Measures how closely the AI evaluator's rubric scores match human judgement.

**Status: no agreement experiment has been run yet.** The dataset ships with
`human_scores` set to `null`. No agreement figure (e.g. "82% agreement") may be quoted
until a real, documented run of the steps below produces it.

## Dataset (`dataset.jsonl`)

30 synthetic items: 10 questions × 3 answers written to span weak / medium / strong.
The candidate, companies and experience are fictional. Fields:

| Field | Meaning |
|---|---|
| `question`, `category`, `evaluation_focus` | The interview question and what it tests |
| `answer` | The candidate answer to score |
| `author_intended_quality` | What the item author aimed for. **Not a label.** |
| `expected_characteristics` | What a strong answer should contain |
| `human_scores` | `clarity`, `specificity`, `result_orientation`, `relevance` (1-5), **filled in by a human** |
| `evaluator_notes` | Optional rater notes |

## Labelling protocol

1. Use the rubric in `app/ai/prompts/answer_evaluation.py` (`RUBRIC`).
2. Score each dimension independently, without looking at AI output.
3. Ideally use two raters, record both, and resolve disagreements >1 point by discussion.
   Record inter-rater agreement too: it is the ceiling for AI-human agreement.
4. Note anything ambiguous in `evaluator_notes`.

## Running

```bash
cd backend
# configure AI_PROVIDER + key in .env (demo provider is a heuristic, not an AI)
python -m evals.run_eval --dataset evals/dataset.jsonl --min-labelled 30
```

The script refuses to report metrics when fewer than `--min-labelled` items have complete
labels. Output goes to `evals/results/<timestamp>/` (`summary.json`, `items.json`).

## Metrics (per dimension)

- **MAE**: mean absolute difference between AI and human scores.
- **Exact agreement**: share of items with identical scores.
- **Within one**: share of items where scores differ by at most 1.
- **Quadratic weighted kappa**: chance-corrected ordinal agreement (`None` when undefined).
- **Mean AI − human**: systematic leniency (+) or harshness (−).
- **Large disagreements**: items with a gap of 2+, as the starting point for error analysis.

## Error analysis template

After a run, record in `evals/results/<timestamp>/analysis.md`:

- Where does the AI systematically differ (e.g. lenient on specificity for long answers)?
- Which question categories disagree most (behavioral vs design)?
- Are disagreements rubric ambiguity, model error, or rater inconsistency?
- What prompt change is proposed, and its new `VERSION`?

Do not tune the prompt purely to maximise agreement on this set; keep a held-out
portion if you iterate on prompts.
