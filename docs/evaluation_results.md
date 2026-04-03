# Evaluation Results

## English Version

### 1. Scope

This document summarizes the evaluation results that are currently stored in the
repository. It reports the prompt set, evaluation process, and batch comparison
results that have already been generated from the existing code.

The current teacher-side evaluation uses the database-course teacher corpus:

- `data/teachers/sql101/`

The current direct model-to-model comparison is stored under:

- `runs/compare_eval/results/`

### 2. Prompt Set Used for Direct Comparison

The direct comparison between the general model and the teacher workflow uses
the shared prompt file:

- `evaluation/prompts/comparison_prompts.jsonl`

This file currently contains five prompts:

| ID | Task | Prompt Focus |
| --- | --- | --- |
| P1 | lesson | SQL injection prevention for an introductory database course |
| P2 | practice | parameterized queries for beginner database students |
| P3 | incident | unsafe SQL query construction in a database course context |
| P4 | lesson | aggregating data with security awareness |
| P5 | practice | secure filtering of query results |

Two example prompts from the current file are:

```text
P1: Write a beginner-friendly lesson on SQL injection prevention for students in an introductory database course. Keep the response within 3-6 sentences. Do not write as dialogue.

P3: Write an incident-style explanation of unsafe SQL query construction in a database course context. Focus on the risk, why it matters, and one defensive mitigation idea. Keep it concise.
```

### 3. Comparison Process

The comparison was produced by `evaluation/batch_compare.py`.

The implemented process is:

1. load the five shared prompts
2. generate one output with the general model
3. generate one output with the teacher workflow
4. evaluate both outputs with the same scoring pipeline
5. save one JSON result file per prompt
6. compute the overall averages

The general model side uses:

- base model + general adapter

The teacher side uses:

- `runtime.workflow.Orchestrator`
- teacher model profile
- optional RAG inside the runtime workflow

In the current comparison script, interactive refinement is suppressed so that
the entire batch can run automatically.

### 4. Result Files

The currently saved comparison files are:

- `runs/compare_eval/results/P1.json`
- `runs/compare_eval/results/P2.json`
- `runs/compare_eval/results/P3.json`
- `runs/compare_eval/results/P4.json`
- `runs/compare_eval/results/P5.json`
- `runs/compare_eval/results/summary.json`

Each per-prompt file stores:

- prompt
- task type
- general output path
- teacher output path
- both evaluation results
- both final scores
- score difference

### 5. Per-Prompt Results

The summary file currently records the following final scores:

| Task ID | General Final Score | Teacher Final Score | Teacher - General |
| --- | --- | --- | --- |
| P1 | 1.55 | 1.55 | 0.00 |
| P2 | 1.78 | 1.78 | 0.00 |
| P3 | 1.78 | 2.00 | +0.22 |
| P4 | 1.43 | 1.65 | +0.22 |
| P5 | 2.00 | 1.78 | -0.22 |

### 6. Aggregate Result

The current overall comparison, from `runs/compare_eval/results/summary.json`,
is:

- `general_avg = 1.708`
- `teacher_avg = 1.752`
- `teacher_minus_general = 0.044`

This means that, on the current five-prompt comparison batch, the teacher
workflow performs slightly better overall than the general model.

### 7. Interpretation of the Current Results

The current results support a cautious interpretation.

#### Prompts where the teacher workflow performed better

- `P3`
  - teacher: `2.00`
  - general: `1.78`
- `P4`
  - teacher: `1.65`
  - general: `1.43`

These two prompts are both strongly tied to database-course framing, so the
teacher workflow appears to help most on prompts where the answer benefits from
course-aware context.

#### Prompts where there was no measurable difference

- `P1`
- `P2`

Both sides received the same final score on these prompts.

#### Prompt where the general model performed better

- `P5`
  - general: `2.00`
  - teacher: `1.78`

So the teacher workflow is not uniformly better on every prompt.

### 8. Important Limitation for Reading the Results

These results should be interpreted together with the current workflow
limitation:

- the batch comparison skipped the interactive two-round refinement path

So the saved scores reflect:

- general model generation
- teacher workflow generation without interactive teacher refinement

They do **not** yet reflect the strongest version of the original runtime
workflow.

### 9. Current Conclusion

Based only on the currently saved batch comparison:

- the teacher workflow is slightly better overall
- the advantage is strongest on some database-context prompts
- the advantage is not uniform across all tasks
- the current result should still be treated as an initial batch comparison,
  not as a final cross-course conclusion

---
