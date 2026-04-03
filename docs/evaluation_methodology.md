# Evaluation Methodology

## English Version

### 1. Scope

This document describes the evaluation workflow that is currently implemented in
the repository. It is based on the code under `evaluation/` and on the prompt
sets and result files already stored in `runs/`.

The current implementation evaluates two output settings:

1. `cybersecurity_eval`
   - used for the general cybersecurity adapter
2. `teacher_eval`
   - used for the teacher-customized runtime workflow

The evaluation pipeline is implemented in:

- `evaluation/prompt_parser.py`
- `evaluation/source_locator.py`
- `evaluation/hard_rules.py`
- `evaluation/llm_judge.py`
- `evaluation/run_eval.py`
- `evaluation/batch_run.py`
- `evaluation/batch_compare.py`

### 2. Evaluation Goal

The current evaluator tries to answer three questions for each generated output:

1. Does the output satisfy the prompt requirement?
2. Does the output reflect learning from the relevant source material?
3. Is the output usable as teaching material?

To do that, the repository combines rule-based checks with a local LLM judge.

### 3. Current Technical Flow

For each sample, the evaluation pipeline runs in the following order.

#### Step 1: Parse the prompt

`evaluation/prompt_parser.py` extracts:

- task type: `lesson`, `practice`, or `incident`
- optional `module_id`
- maximum character limit
- sentence-range constraint
- dialogue prohibition
- retrieval terms

For example, from the comparison prompt:

```text
Write a beginner-friendly lesson on SQL injection prevention for students in an introductory database course. Keep the response within 3-6 sentences. Do not write as dialogue.
```

the parser can recover:

- `task_type = lesson`
- `sentence_range = [3, 6]`
- `no_dialogue = true`
- retrieval terms related to `SQL` and `lesson`

#### Step 2: Locate source material

`evaluation/source_locator.py` then searches for likely source files.

- For `cybersecurity_eval`, it searches under:
  - `generated_modules/21 Modules/`
- For `teacher_eval`, it searches under:
  - `data/teachers/`

The current locator ranks candidate files by retrieval-term matches in:

- filenames
- the first part of file content

It returns up to three source snippets for later semantic judgment.

#### Step 3: Run hard-rule evaluation

`evaluation/hard_rules.py` checks prompt-visible constraints.

The current implemented checks are:

- `length_ok`
- `sentence_ok`
- `no_dialogue_ok`
- `task_shape_ok`

These are deterministic checks. The hard-rule score is kept on a `0-2` scale.

#### Step 4: Run the LLM judge

`evaluation/llm_judge.py` loads the local base model as a judge and sends it a
structured evaluation prompt.

The judge prompt explicitly asks the model to score only these three dimensions:

1. `prompt_match`
2. `source_learning`
3. `teaching_usefulness`

The output must be strict JSON with the following keys:

```json
{
  "prompt_match_score": 0,
  "source_learning_score": 0,
  "teaching_usefulness_score": 0,
  "reason": ["", "", ""]
}
```

The current scoring rubric is:

- `2 = clearly satisfies`
- `1 = partially satisfies`
- `0 = does not satisfy`

The LLM judge prompt in the code also explicitly tells the model that
`source_learning` should check whether the output:

- covers key concepts from the source
- preserves the main instructional intent
- does not drift away from the source topic

#### Step 5: Combine scores

`evaluation/run_eval.py` computes the final score as:

```text
llm_avg = (prompt_match_score + source_learning_score + teaching_usefulness_score) / 3
final_score = 0.35 * hard_score + 0.65 * llm_avg
```

This `final_score` is the repository's main per-sample score.

### 4. Single-Output Evaluation

The repository supports single-output evaluation through:

```bash
python -m evaluation.run_eval \
  --model-type cybersecurity_eval \
  --prompt "<prompt>" \
  --output-file <generated_output_file> \
  --save-json <result_file>
```

The same script can also evaluate `teacher_eval` outputs by changing the
`--model-type` argument.

### 5. Batch Evaluation

The repository currently includes prompt files for batch evaluation:

- `evaluation/prompts/cybersecurity_prompts.jsonl`
- `evaluation/prompts/teacher_prompts.jsonl`
- `evaluation/prompts/comparison_prompts.jsonl`

The comparison file currently contains five shared prompts:

- `P1`: lesson on SQL injection prevention
- `P2`: practice on parameterized queries
- `P3`: incident-style explanation of unsafe SQL query construction
- `P4`: lesson on aggregating data with security awareness
- `P5`: practice on secure filtering of query results

The comparison workflow is implemented in `evaluation/batch_compare.py`.

Its current behavior is:

1. load the prompt set
2. generate output with the general model
3. generate output with the teacher workflow
4. evaluate both outputs with the same evaluator
5. save per-prompt JSON comparison files
6. compute overall averages

### 6. Current Prompt and Generation Setup

The current comparison uses:

- general model:
  - base model + general adapter
- teacher model:
  - `runtime.workflow.Orchestrator` with `model_profile="teacher"`

In the current implementation of `batch_compare.py`, the teacher side resets
shared memory and bypasses interactive feedback by forcing:

```python
builtins.input = lambda _prompt="": ""
```

This means the current comparison does **not** execute the original two-round
interactive refinement process, even though the runtime workflow supports it.

### 7. Current Batch Results

The current comparison summary is stored in:

- `runs/compare_eval/results/summary.json`

The recorded results are:

| Task ID | General Final Score | Teacher Final Score | Delta |
| --- | --- | --- | --- |
| P1 | 1.55 | 1.55 | 0.00 |
| P2 | 1.78 | 1.78 | 0.00 |
| P3 | 1.78 | 2.00 | +0.22 |
| P4 | 1.43 | 1.65 | +0.22 |
| P5 | 2.00 | 1.78 | -0.22 |

The aggregate averages are:

- `general_avg = 1.708`
- `teacher_avg = 1.752`
- `teacher_minus_general = 0.044`

Based on the current batch only, the teacher workflow performs slightly better
overall, but not uniformly better on every prompt.

### 8. Current Limitations

The current evaluation is already functional, but it has several limitations
that follow directly from the implemented code:

1. the teacher side currently uses only one teacher-course family:
   - `sql101`
2. the shared comparison prompt set contains only five prompts
3. the comparison currently skips the interactive two-round refinement step
4. the semantic scoring is still produced by the local LLM judge rather than by
   human correction

### 9. Purpose of This Document

This document records the current implemented evaluation methodology exactly as
it exists in the repository. It describes the actual prompt flow, scoring logic,
and currently saved comparison results.

---

## 中文翻译

### 1. 范围

这份文档描述的是当前仓库中已经实现的 evaluation workflow。内容基于
`evaluation/` 目录下的代码，以及 `runs/` 目录里已经保存的 prompt 和结果文件。

当前实现主要评估两类输出：

1. `cybersecurity_eval`
   - 用于 general cybersecurity adapter 的输出
2. `teacher_eval`
   - 用于 teacher-customized runtime workflow 的输出

整个评估流程主要由以下脚本实现：

- `evaluation/prompt_parser.py`
- `evaluation/source_locator.py`
- `evaluation/hard_rules.py`
- `evaluation/llm_judge.py`
- `evaluation/run_eval.py`
- `evaluation/batch_run.py`
- `evaluation/batch_compare.py`

### 2. 评估目标

当前 evaluator 主要试图回答三个问题：

1. 输出是否满足 prompt 的要求？
2. 输出是否体现了对相关 source material 的学习？
3. 输出是否能作为教学材料使用？

为了回答这三个问题，当前仓库把规则检查和本地 LLM judge 结合起来使用。

### 3. 当前技术流程

对于每条样本，当前 evaluation pipeline 按如下顺序运行。

#### 第一步：解析 prompt

`evaluation/prompt_parser.py` 负责抽取：

- 任务类型：`lesson`、`practice` 或 `incident`
- 可选的 `module_id`
- 最大字符限制
- 句数范围限制
- 是否禁止对话体
- retrieval terms

例如，对于这条 comparison prompt：

```text
Write a beginner-friendly lesson on SQL injection prevention for students in an introductory database course. Keep the response within 3-6 sentences. Do not write as dialogue.
```

parser 可以恢复出：

- `task_type = lesson`
- `sentence_range = [3, 6]`
- `no_dialogue = true`
- 与 `SQL`、`lesson` 相关的检索词

#### 第二步：定位 source material

`evaluation/source_locator.py` 接着去查找可能相关的 source files。

- 对于 `cybersecurity_eval`，它搜索：
  - `generated_modules/21 Modules/`
- 对于 `teacher_eval`，它搜索：
  - `data/teachers/`

当前 locator 的排序依据是 retrieval terms 在以下两处的匹配情况：

- 文件名
- 文件内容前部

最后返回最多三个 source snippets，供后续语义判断使用。

#### 第三步：执行 hard-rule evaluation

`evaluation/hard_rules.py` 负责检查 prompt 中显式可判断的约束。

当前已经实现的检查包括：

- `length_ok`
- `sentence_ok`
- `no_dialogue_ok`
- `task_shape_ok`

这些都是确定性的规则检查。hard-rule score 保持在 `0-2` 的范围内。

#### 第四步：执行 LLM judge

`evaluation/llm_judge.py` 会加载本地 base model 作为 judge，并向它发送结构化的
evaluation prompt。

judge prompt 明确要求模型只评三个维度：

1. `prompt_match`
2. `source_learning`
3. `teaching_usefulness`

输出必须是严格 JSON，字段如下：

```json
{
  "prompt_match_score": 0,
  "source_learning_score": 0,
  "teaching_usefulness_score": 0,
  "reason": ["", "", ""]
}
```

当前评分规则是：

- `2 = clearly satisfies`
- `1 = partially satisfies`
- `0 = does not satisfy`

代码中的 judge prompt 还明确要求模型在评估 `source_learning` 时检查：

- 是否覆盖 source 中的关键概念
- 是否保留主要教学意图
- 是否没有偏离原主题

#### 第五步：合并分数

`evaluation/run_eval.py` 按如下方式计算最终分数：

```text
llm_avg = (prompt_match_score + source_learning_score + teaching_usefulness_score) / 3
final_score = 0.35 * hard_score + 0.65 * llm_avg
```

这个 `final_score` 是当前仓库里每条样本的主要评分结果。

### 4. 单条评估

仓库支持通过如下方式对单个输出做 evaluation：

```bash
python -m evaluation.run_eval \
  --model-type cybersecurity_eval \
  --prompt "<prompt>" \
  --output-file <generated_output_file> \
  --save-json <result_file>
```

如果要评估 `teacher_eval` 输出，只需要调整 `--model-type` 即可。

### 5. 批量评估

当前仓库中已经包含用于批量评估的 prompt 文件：

- `evaluation/prompts/cybersecurity_prompts.jsonl`
- `evaluation/prompts/teacher_prompts.jsonl`
- `evaluation/prompts/comparison_prompts.jsonl`

目前 comparison prompt 文件里包含五条共享 prompt：

- `P1`: 关于 SQL injection prevention 的 lesson
- `P2`: 关于 parameterized queries 的 practice
- `P3`: 关于 unsafe SQL query construction 的 incident-style explanation
- `P4`: 关于 aggregating data with security awareness 的 lesson
- `P5`: 关于 secure filtering of query results 的 practice

comparison workflow 实现在 `evaluation/batch_compare.py` 中。

它当前的运行逻辑是：

1. 读取 prompt set
2. 用 general model 生成输出
3. 用 teacher workflow 生成输出
4. 用同一个 evaluator 对两边输出打分
5. 保存每条 prompt 的对比 JSON 文件
6. 计算整体平均分

### 6. 当前 prompt 与生成设置

当前 comparison 使用的是：

- general model：
  - base model + general adapter
- teacher model：
  - `runtime.workflow.Orchestrator`，并设置 `model_profile="teacher"`

在当前 `batch_compare.py` 的实现里，teacher 侧会重置 shared memory，并通过：

```python
builtins.input = lambda _prompt="": ""
```

强制跳过交互式输入。

这意味着当前 comparison **并没有真正执行** runtime 原本支持的两轮 interactive
refinement，尽管这个机制在 workflow 本身中是存在的。

### 7. 当前批量结果

当前 comparison summary 保存在：

- `runs/compare_eval/results/summary.json`

记录到的结果如下：

| Task ID | General Final Score | Teacher Final Score | Delta |
| --- | --- | --- | --- |
| P1 | 1.55 | 1.55 | 0.00 |
| P2 | 1.78 | 1.78 | 0.00 |
| P3 | 1.78 | 2.00 | +0.22 |
| P4 | 1.43 | 1.65 | +0.22 |
| P5 | 2.00 | 1.78 | -0.22 |

整体平均分为：

- `general_avg = 1.708`
- `teacher_avg = 1.752`
- `teacher_minus_general = 0.044`

仅根据当前这一批结果，teacher workflow 在整体上略优于 general model，但并不是
在每一条 prompt 上都更好。

### 8. 当前局限

当前 evaluation 已经可以工作，但它仍然存在一些由现有实现直接带来的局限：

1. teacher 侧目前只使用了一个 teacher-course family：
   - `sql101`
2. comparison prompt set 目前只有五条 prompt
3. 当前 comparison 跳过了 interactive 的两轮 refinement
4. 语义评分仍然由本地 LLM judge 完成，而不是由人工校正

### 9. 这份文档的作用

这份文档记录的是当前仓库中已经存在的、真实实现的 evaluation methodology。它
描述了实际的 prompt 流程、评分逻辑，以及当前已经保存下来的 comparison 结果。
