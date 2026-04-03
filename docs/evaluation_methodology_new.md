# Evaluation Methodology New

## English Version

### 1. Scope

This document describes a proposed extension to the current evaluation
methodology. It is not fully implemented in the repository yet. It is a design
direction built on top of the current runtime and evaluation code.

The design is grounded in components that already exist in the repository:

- the current evaluator already outputs structured dimension scores
- the runtime workflow already supports up to two rounds of refinement
- the repository already stores generation traces and comparison results

The new part is the planned addition of teacher correction on top of the
existing evaluator output.

### 2. Starting Point in the Current Repository

The current repository already has two relevant mechanisms:

1. `runtime/workflow/orchestrator.py`
   - generates an answer
   - verifies it
   - supports up to two refinement rounds by accepting feedback from `input()`
2. `evaluation/`
   - parses prompts
   - retrieves source material
   - scores outputs with hard rules and an LLM judge

At the moment, these two mechanisms are mostly separate:

- the runtime refinement loop improves the answer
- the evaluator scores the answer afterward

The proposed extension is to connect them more tightly.

### 3. Proposed Technical Idea

The current evaluator already returns structured scores:

- `prompt_match_score`
- `source_learning_score`
- `teaching_usefulness_score`

The new plan is to let the teacher inspect those scores and correct them when
necessary, instead of letting the evaluator remain fully automatic.

The proposed flow is:

1. the model generates an answer
2. the evaluator scores the answer using the current rubric
3. the teacher reviews:
   - the generated answer
   - the evaluator's per-dimension scores
   - the evaluator's reasons
4. the teacher may:
   - keep a score unchanged
   - revise one or more scores
   - add refinement feedback on the answer
5. the system uses that feedback in the next refinement round
6. this can repeat for up to two rounds, matching the current runtime design

### 4. Proposed Data to Record

If this design is implemented, each refinement round should store:

- original prompt
- generated output for the round
- evaluator scores for the round
- evaluator reasons for the round
- teacher-corrected scores
- teacher textual feedback
- revised output from the next round

That would create a structured feedback trajectory rather than only a final
answer.

### 5. Why This Extension Fits the Existing Repository

This proposal is consistent with the current codebase because it extends, rather
than replaces, the current architecture.

It uses:

- the existing runtime refinement loop in `orchestrator.py`
- the existing evaluator dimensions in `llm_judge.py`
- the current trace-oriented workflow already present in `runs/<run_id>/`

So the proposal is best understood as:

- current system:
  - generator -> evaluator
- proposed system:
  - generator -> evaluator -> teacher correction -> refinement -> evaluator

### 6. Expected Benefits

The expected value of the proposed design is in two directions.

#### 1. Better evaluator calibration

If the teacher corrects evaluator scores, the project can collect examples of:

- over-scoring
- under-scoring
- disagreement per evaluation dimension

This would make it possible to study whether the evaluator actually matches the
teacher's standard.

#### 2. Better generation supervision

The teacher-corrected scores and revision feedback would also create a richer
signal for future generation improvement.

Instead of storing only:

- prompt -> final answer

the system could store:

- prompt -> draft answer -> evaluator judgment -> teacher correction ->
  revised answer

This is especially relevant for teacher-customized educational generation,
because it records not only whether an answer was preferred, but also why it was
judged insufficient and how it was revised.

### 7. Relation to Preference Optimization

This proposed extension does not mean that the current repository has already
implemented preference optimization or RLHF training.

What it would do is prepare structured human feedback data that may later be
useful for methods such as:

- preference supervision
- supervised refinement learning
- `DPO`-style optimization
- other preference-based methods

At the current stage, those methods are not yet implemented in the repository.
This document only states that the proposed teacher-corrected evaluation design
could prepare cleaner data for that future direction.

### 8. Current Status

This design is still proposed rather than fully implemented.

What already exists:

- two-round runtime refinement support
- structured evaluator dimensions
- comparison prompt sets
- saved evaluation results

What is not yet implemented:

- teacher correction of evaluator scores
- structured storage of corrected scores per round
- training on those corrected trajectories

### 9. Purpose of This Document

This document records the next evaluation direction under consideration. It is
meant to be read together with the current `evaluation_methodology.md`, which
documents the already implemented baseline workflow.

---

## 中文翻译

### 1. 范围

这份文档描述的是对当前 evaluation methodology 的一个拟议扩展方案。它目前
还没有在仓库中完整实现，而是在当前 runtime 和 evaluation 代码基础上提出的
一个设计方向。

这个设计是建立在仓库里已经存在的组件之上的：

- 当前 evaluator 已经会输出结构化的各维度分数
- 当前 runtime workflow 已经支持最多两轮 refinement
- 仓库已经会保存 generation traces 和 comparison results

新的部分，是计划在现有 evaluator 输出之上再加入教师修正这一环节。

### 2. 当前仓库中的起点

当前仓库里已经有两个相关机制：

1. `runtime/workflow/orchestrator.py`
   - 负责生成答案
   - 做 verifier 检查
   - 通过 `input()` 支持最多两轮 refinement
2. `evaluation/`
   - 负责解析 prompt
   - 检索 source material
   - 用 hard rules 和 LLM judge 对输出打分

目前这两套机制大体上还是分开的：

- runtime refinement loop 负责改进答案
- evaluator 在答案生成之后再做评分

这个新方案的核心，就是把这两者连接得更紧密。

### 3. 拟议的技术想法

当前 evaluator 已经会返回结构化分数：

- `prompt_match_score`
- `source_learning_score`
- `teaching_usefulness_score`

新的计划是：让教师在必要时检查并修正这些分数，而不是让 evaluator 永远保持为
完全自动的评分器。

我设想中的流程是：

1. 模型先生成回答
2. evaluator 按当前 rubric 自动打分
3. 教师查看：
   - 生成的回答
   - evaluator 在每个维度上的分数
   - evaluator 给出的理由
4. 教师可以：
   - 保持某一项分数不变
   - 修改一个或多个维度的分数
   - 对回答本身追加 refinement feedback
5. 系统把这些反馈带入下一轮 refinement
6. 整个过程最多重复两轮，与当前 runtime 的设计保持一致

### 4. 拟议需要记录的数据

如果这个设计被实现，那么每一轮 refinement 都应当保存：

- 原始 prompt
- 本轮生成输出
- 本轮 evaluator 分数
- 本轮 evaluator 理由
- 教师修正后的分数
- 教师文字反馈
- 下一轮修订后的输出

这样系统最终得到的就不只是一个最终答案，而是一条结构化的反馈轨迹。

### 5. 为什么这个扩展适合当前仓库

这个方案与当前代码库是一致的，因为它是在扩展现有架构，而不是推翻重写。

它复用了：

- `orchestrator.py` 中已经存在的 runtime refinement loop
- `llm_judge.py` 中已经存在的 evaluator 维度
- 当前 `runs/<run_id>/` 下已经存在的 trace-oriented workflow

所以更准确地说：

- 当前系统：
  - generator -> evaluator
- 拟议系统：
  - generator -> evaluator -> teacher correction -> refinement -> evaluator

### 6. 预期收益

这个设计预期的价值主要体现在两个方向。

#### 1. 更好的 evaluator calibration

如果教师会去修正 evaluator 的分数，那么项目就能积累一些新的监督样本，例如：

- 哪些情况 evaluator 打高了
- 哪些情况 evaluator 打低了
- 不同 evaluation 维度上教师与 evaluator 的分歧

这样就能进一步研究 evaluator 是否真的符合教师标准。

#### 2. 更好的生成监督信号

教师修正后的分数和 revision feedback，也会形成一种更丰富的生成优化信号。

系统不再只保存：

- prompt -> final answer

而是可以保存：

- prompt -> draft answer -> evaluator judgment -> teacher correction ->
  revised answer

对于 teacher-customized educational generation 来说，这一点尤其重要，因为它不仅
记录“哪个答案更好”，还记录“为什么它不够好”以及“它是怎样被改好的”。

### 7. 与 preference optimization 的关系

这个拟议扩展并不意味着当前仓库已经实现了 preference optimization 或 RLHF
训练。

它真正能做的是为未来可能的方法准备结构化的人类反馈数据，例如：

- preference supervision
- supervised refinement learning
- `DPO` 风格的优化
- 其他基于 preference 的方法

在当前阶段，这些方法都还没有在仓库中实现。这里的意思只是：如果实现了这种
teacher-corrected evaluation 设计，那么未来可能为这些方向准备更干净的数据。

### 8. 当前状态

这个设计目前仍然是一个 proposal，而不是完整实现。

已经存在的部分：

- 两轮 runtime refinement 支持
- 结构化 evaluator 维度
- comparison prompt sets
- 已保存的 evaluation results

还没有实现的部分：

- 教师对 evaluator 分数的修正
- 每轮 corrected scores 的结构化保存
- 利用这些 corrected trajectories 进行训练

### 9. 这份文档的作用

这份文档记录的是当前正在考虑的下一步 evaluation 方向。它应当与当前的
`evaluation_methodology.md` 一起阅读：前者描述的是已经实现的 baseline
workflow，后者描述的是下一步准备扩展的设计。
