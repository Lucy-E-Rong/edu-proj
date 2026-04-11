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

## 中文翻译

### 1. 范围

这份文档总结的是当前已经保存在仓库中的 evaluation 结果。它报告了已经实际运行过
的 prompt set、evaluation process，以及 batch comparison 的真实结果。

当前 teacher 侧 evaluation 使用的是数据库课程 teacher corpus：

- `data/teachers/sql101/`

当前直接的 model-to-model comparison 保存在：

- `runs/compare_eval/results/`

### 2. 用于直接比较的 prompt set

general model 和 teacher workflow 的直接对比使用的是这份共享 prompt 文件：

- `evaluation/prompts/comparison_prompts.jsonl`

这个文件目前包含五条 prompt：

| ID | Task | Prompt Focus |
| --- | --- | --- |
| P1 | lesson | 面向数据库入门课程的 SQL injection prevention |
| P2 | practice | 面向初学者数据库学生的 parameterized queries |
| P3 | incident | 数据库课程语境下的 unsafe SQL query construction |
| P4 | lesson | 带有 security awareness 的 aggregating data |
| P5 | practice | secure filtering of query results |

当前文件中的两条示例 prompt 是：

```text
P1: Write a beginner-friendly lesson on SQL injection prevention for students in an introductory database course. Keep the response within 3-6 sentences. Do not write as dialogue.

P3: Write an incident-style explanation of unsafe SQL query construction in a database course context. Focus on the risk, why it matters, and one defensive mitigation idea. Keep it concise.
```

### 3. 对比流程

这组 comparison 是通过 `evaluation/batch_compare.py` 生成的。

当前实现的流程是：

1. 读取这五条共享 prompt
2. 用 general model 各生成一条输出
3. 用 teacher workflow 各生成一条输出
4. 用同一套 scoring pipeline 对两边输出打分
5. 每条 prompt 保存一个 JSON 结果文件
6. 计算整体平均分

general model 一侧使用的是：

- base model + general adapter

teacher 一侧使用的是：

- `runtime.workflow.Orchestrator`
- teacher model profile
- runtime workflow 内的 optional RAG

在当前 comparison script 中，为了让 batch 自动跑完，interactive refinement 被
关闭了。

### 4. 结果文件

当前已保存的 comparison 文件包括：

- `runs/compare_eval/results/P1.json`
- `runs/compare_eval/results/P2.json`
- `runs/compare_eval/results/P3.json`
- `runs/compare_eval/results/P4.json`
- `runs/compare_eval/results/P5.json`
- `runs/compare_eval/results/summary.json`

每条 prompt 的结果文件中都保存了：

- prompt
- task type
- general output path
- teacher output path
- 两边各自的 evaluation result
- 两边各自的 final score
- 分数差值

### 5. 每条 prompt 的结果

当前 summary 文件记录到的 final scores 如下：

| Task ID | General Final Score | Teacher Final Score | Teacher - General |
| --- | --- | --- | --- |
| P1 | 1.55 | 1.55 | 0.00 |
| P2 | 1.78 | 1.78 | 0.00 |
| P3 | 1.78 | 2.00 | +0.22 |
| P4 | 1.43 | 1.65 | +0.22 |
| P5 | 2.00 | 1.78 | -0.22 |

### 6. 整体结果

根据 `runs/compare_eval/results/summary.json`，当前整体对比结果为：

- `general_avg = 1.708`
- `teacher_avg = 1.752`
- `teacher_minus_general = 0.044`

这意味着，在当前这五条 prompt 的 comparison batch 上，teacher workflow 在
整体上略优于 general model。

### 7. 当前结果的解释

当前结果支持一种比较谨慎的解释。

#### teacher workflow 表现更好的 prompt

- `P3`
  - teacher: `2.00`
  - general: `1.78`
- `P4`
  - teacher: `1.65`
  - general: `1.43`

这两条 prompt 都和数据库课程语境关系比较强，因此目前看起来，teacher workflow
更容易在这种需要 course-aware context 的任务上体现优势。

#### 没有明显差异的 prompt

- `P1`
- `P2`

这两条 prompt 上，双方得到的 final score 相同。

#### general model 表现更好的 prompt

- `P5`
  - general: `2.00`
  - teacher: `1.78`

因此，teacher workflow 并不是在所有 prompt 上都更好。

### 8. 解释这些结果时必须注意的限制

这些结果必须和当前 workflow 的一个限制一起理解：

- batch comparison 跳过了 interactive 的两轮 refinement 路径

因此，现在保存下来的分数反映的是：

- general model 的生成结果
- 不带 interactive teacher refinement 的 teacher workflow 生成结果

它们**还没有**体现原始 runtime workflow 最强版本下的效果。

### 9. 当前结论

仅根据当前已经保存的 batch comparison，可以得出：

- teacher workflow 在整体上略优于 general model
- 它的优势主要体现在部分数据库语境较强的 prompt 上
- 这种优势并不是对所有任务都一致成立
- 当前结果更适合作为一轮初步的 batch comparison，而不是最终的跨课程结论
