# 通用网络安全模型与教师定制模型评估方案

## 1. 目的

本方案用于评估两个对象：

1. `general cybersecurity model`
2. `teacher-customized model`

评估目标不是只看模型能不能生成文字，而是看输出是否：

- 满足 prompt 的硬性要求
- 与来源内容契合
- 学到了对应领域或课程材料
- 具有教学上的可用性

更具体地说，本方案主要围绕以下三个核心问题展开：

1. prompt 要求有没有满足
2. 内容是不是从来源里学来的
3. 教学上能不能用

本方案包括两类评估：

1. `硬性评估`
2. `LLM 评估`

其中，硬性评估负责可量化部分，LLM 评估负责语义和内容契合部分。

当前仓库中，这套评估流程已经实现到 `evaluation/` 目录，主要包括：

- `evaluation/prompt_parser.py`
- `evaluation/source_locator.py`
- `evaluation/hard_rules.py`
- `evaluation/llm_judge.py`
- `evaluation/run_eval.py`
- `evaluation/batch_run.py`
- `evaluation/prompts/cybersecurity_prompts.jsonl`
- `evaluation/prompts/teacher_prompts.jsonl`

## 2. 评估对象

### 2.1 General cybersecurity model

`general cybersecurity model` 指基础模型加载通用网络安全 adapter 后的输出。

建议通过以下方式生成样本：

```bash
python training/infer_with_adapter.py \
  --adapter runs/<general_run_id>/adapter \
  --prompt "<evaluation_prompt>" \
  --out runs/<eval_run_id>/cybersecurity/<sample_id>.md \
  --save_prompt
```

当前批量脚本默认使用的 general adapter 路径是：

```text
runs/20260313_140305_general_train/adapter
```

### 2.2 Teacher-customized model

`teacher-customized model` 指 teacher adapter 在当前 runtime 流程中的最终输出。

此处固定包含：

- teacher adapter
- orchestrator
- CAG
- RAG

建议通过以下方式生成样本：

```bash
python -m runtime.app.cli lesson --model-profile teacher "<evaluation_prompt>"
python -m runtime.app.cli practice --model-profile teacher "<evaluation_prompt>"
python -m runtime.app.cli incident --model-profile teacher "<evaluation_prompt>"
```

在当前实现中，teacher 样本由批量脚本自动完成：

1. 调用 `runtime.app.cli`
2. 从命令行输出中提取纯生成内容
3. 保存为单独文件
4. 再交给 evaluator 做评估

## 3. 总体思路

整个评估流程分为四步：

1. 从 prompt 中抽取关键词和约束
2. 对来源内容进行定位与检索
3. 先做硬性评估
4. 再做 LLM 评估

这里的关键点是：

- 规则优先
- LLM 补充
- LLM 不直接包办全部评估

## 4. 关键词分类

从 prompt 中抽取关键词后，系统对关键词做三类处理：

1. 哪些词可以直接用于硬性评估
2. 哪些词需要交给 LLM 做语义判断
3. 哪些词可以用于定位来源目录和来源内容

建议先由规则抽取显式约束，再由 LLM 补充隐含要求。

例如：

- `300字以内`
- `3-6句话`
- `lesson`
- `practice`
- `incident`
- `module_008`

这些都可以先由规则直接识别。

对于较隐含的要求，例如：

- `beginner-friendly`
- `简短但清楚`
- `更像课堂材料`

再交给 LLM 做补充分类。

建议 LLM 输出固定 JSON：

```json
{
  "hard_rules": ["300字以内", "3-6句话", "简短回答"],
  "llm_judge": ["beginner-friendly", "内容契合度", "教学实用性"],
  "retrieval_terms": ["lesson", "module_008", "Aggregating Data"]
}
```

## 5. 来源目录定位

评估时需要根据关键词定位来源内容。

### 5.1 General cybersecurity model 的来源目录

通用网络安全内容主要对应：

- `generated_modules/21 Modules/`

该目录下每个模块包含：

- `security_incident_document.md`
- `security_lesson_document.md`
- `security_practice_document.md`

因此，如果 prompt 中出现：

- `lesson`
- `practice`
- `incident`
- `module_008`
- 漏洞标题或主题词

就可以先由程序定位到对应模块，再在对应文档中搜索相关内容。

### 5.2 Teacher-customized model 的来源目录

teacher 相关内容主要对应：

- `data/teachers/`

当前仓库中可以优先使用：

- `data/teachers/sql101/extracted/blocks.jsonl`
- `data/teachers/sql101/processed/train.jsonl`
- `data/teachers/sql101/processed/eval.jsonl`
- `data/teachers/sql101/original/` 下的原始材料

因此，如果 prompt 中出现：

- `Aggregating Data`
- `Lesson 1`
- 某章节名
- 某课程主题词

就可以先在 `data/teachers/` 下搜索这些关键词，再抽取对应内容作为评估参考。

### 5.3 来源检索失败时的处理

来源检索不一定每次都能精确命中，因此建议按以下顺序做 fallback：

1. 先做文件名或标题精确匹配
2. 再做关键词搜索
3. 再做模糊匹配
4. 如果仍然找不到，则标记为 `source_not_found`

当 `source_not_found` 时：

- 硬性评估仍可继续
- LLM 评估中“来源学习情况”应标记为无法充分判断，而不是强行给高分

## 6. 评估结构

本方案只有两个评分模块：

1. `硬性评估`
2. `LLM 评估`

最终总分可由这两部分合并得到。

当前代码里，最终分数按以下权重合并：

- 硬性评估：`35%`
- LLM 评估：`65%`

---

## 7. 硬性评估

硬性评估只负责可明确量化的部分，重点检查：

- 格式
- 长度
- 句子数
- 是否出现禁止内容
- 是否完成了 prompt 中明确要求的结构

### 7.1 适合硬性评估的内容

例如 prompt 中出现以下要求时，都可以直接程序化判断：

- `300字以内`
- `3-6句话`
- `简短回答`
- `输出 only final answer`
- `不要写成对话`
- `包含 example`
- `包含 practice question`

### 7.2 硬性评估规则

建议至少包含以下几项：

#### 1. 长度检查

- 字数是否超过上限
- 句子数是否在要求范围内

#### 2. 格式检查

- 是否为对话体，不应该是对话体
- 是否出现 `user:`、`assistant:`、`system:`
- 是否包含要求的 section 或标题

#### 3. 任务类型检查

- `lesson` 是否像 lesson
- `practice` 是否像 practice
- `incident` 是否像 incident

这一项可以先做基础规则判断，例如：

- `lesson` 至少要有解释性语句
- `practice` 至少要有任务或问题
- `incident` 至少要有事件、风险或缓解信息

### 7.3 硬性评估 rubric

每个子项都可以按 `0/1/2` 打分：

`2 分`
- 完全满足

`1 分`
- 基本满足，但有轻微偏差

`0 分`
- 明显不满足

硬性评估总分可以取平均值，或者按权重汇总。

当前代码里的硬性评估输出形式大致如下：

```json
{
  "score": 1.5,
  "checks": {
    "length_ok": true,
    "sentence_ok": true,
    "no_dialogue_ok": true,
    "task_shape_ok": false
  }
}
```

---

## 8. LLM 评估

LLM 评估主要负责规则不好判断的部分。这里不再拆很多独立指标，而是集中评估以下三类问题：

1. 输出内容是否契合 prompt
2. 输出是否从来源内容中学到了东西
3. 输出是否满足教学实用性

这种设计比铺很多分散的小指标更实用，因为它更直接对应本项目真正关心的问题：输出是否满足要求、是否利用了来源内容、以及是否真的适合教学使用。

### 8.1 LLM 评估输入

建议输入给 LLM 的内容包括：

- 原始 prompt
- 模型输出
- 从来源目录中检索到的相关文本
- 当前任务类型

### 8.2 LLM 评估重点

#### 1. 内容契合度

检查输出是否真正回应了 prompt，而不是只碰到一些关键词。

例如：

- prompt 要求 beginner-friendly lesson
- 输出是否真的适合 beginner
- prompt 要求与数据库课程相关
- 输出是否真的落在该课程语境中

#### 2. 来源学习情况

检查输出中有多少内容可以追溯到来源目录中的相关材料。

这里重点不是逐字匹配，而是判断：

- 是否吸收了来源中的概念
- 是否保留了来源中的重点内容
- 是否只是泛泛生成，与来源内容关系很弱

这里要注意：评估目标不是检查模型有没有“抄写来源内容”，而是检查它有没有真正学到或利用来源中的关键内容。

也就是说，这里要评的不是：

- 模型有没有抄来源内容

而是：

- 模型有没有学到来源内容

更合适的判断方式是看三类东西：

1. 是否覆盖来源中的关键概念
2. 是否保持了来源中的主要教学意图
3. 是否没有明显偏离来源主题

#### 3. 教学实用性

检查输出是否适合教学使用，例如：

- 是否清楚
- 是否有组织
- 是否适合拿来给学生看
- 是否有实际教学价值

这里的“教学实用性”不再单独扩展成很大的抽象指标，而是只回答一个实际问题：

- 这段输出能不能直接拿来当 lesson、practice 或 incident 材料使用

具体判断时，可以重点看：

1. 是否适合直接给学生阅读
2. 是否表达清楚
3. 是否结构清晰
4. 是否适合作为课堂 lesson/practice 材料

### 8.3 LLM 评估输出格式

建议强制要求 LLM 返回结构化 JSON：

```json
{
  "prompt_match_score": 2,
  "source_learning_score": 1,
  "teaching_usefulness_score": 2,
  "reason": [
    "输出与 prompt 高度相关",
    "引用了来源中的核心概念",
    "整体可用于教学，但与来源内容的贴合度仍可更强"
  ]
}
```

### 8.4 LLM 评估 rubric

同样建议使用 `0/1/2`：

`2 分`
- 明显满足

`1 分`
- 部分满足

`0 分`
- 明显不满足

当前代码要求本地 8B 模型返回严格 JSON，字段包括：

```json
{
  "prompt_match_score": 2,
  "source_learning_score": 1,
  "teaching_usefulness_score": 2,
  "reason": [
    "输出与 prompt 高度相关",
    "覆盖了来源中的关键概念",
    "整体可用于教学，但还可以更贴近来源内容"
  ]
}
```

---

## 9. 推荐实现流程

建议实现流程如下：

### 第一步：读取 prompt

输入一条 evaluation prompt。

### 第二步：抽取关键词和约束

先对 prompt 做关键词抽取和约束抽取。

### 第三步：规则分类，LLM 补充

先由规则将关键词分成三类：

- 硬性评估关键词
- LLM 评估关键词
- 来源检索关键词

再由 LLM 补充规则没有识别出来的隐含要求。

### 第四步：定位来源内容

根据关键词决定去哪个目录搜索：

- `generated_modules/21 Modules/`
- `data/teachers/`

然后检索相关文件和相关片段。

### 第五步：执行硬性评估

对输出进行：

- 字数检查
- 句数检查
- 格式检查
- 结构检查

### 第六步：执行 LLM 评估

把 prompt、output、来源内容一起交给 LLM，判断：

- 内容契合度
- 是否学到了来源内容
- 教学实用性

### 第七步：汇总结果

输出最终结果表，例如：

```json
{
  "sample_id": "lesson_001",
  "model_type": "cybersecurity_eval",
  "hard_score": 1.67,
  "llm_score": 1.67,
  "final_score": 1.67
}
```

## 10. 当前已实现的运行方式

### 10.1 单条评估

当你已经有一条输出文件时，可以直接运行：

```bash
python -m evaluation.run_eval \
  --model-type cybersecurity_eval \
  --prompt "Write a beginner-friendly lesson for module_008: ArrayOS AG DesktopDirect Real Exploit. Explain the main security issue and why it matters. Keep the response within 3-6 sentences." \
  --output-file runs/eval_single/cyber_C4.md \
  --save-json runs/eval_single/cyber_C4_eval.json
```

teacher 模型也可以用同样方式，只需要把 `model-type` 改成 `teacher_eval`。

### 10.2 批量评估

当前仓库中已经提供两组批量 prompt，各 5 条：

- `evaluation/prompts/cybersecurity_prompts.jsonl`
- `evaluation/prompts/teacher_prompts.jsonl`

批量命令如下：

```bash
python -m evaluation.batch_run --target cybersecurity
python -m evaluation.batch_run --target teacher
python -m evaluation.batch_run --target all
```

默认批量输出目录：

- `runs/batch_eval/cybersecurity/generated/`
- `runs/batch_eval/cybersecurity/results/`
- `runs/batch_eval/teacher/generated/`
- `runs/batch_eval/teacher/results/`

## 11. 结果记录方式

建议每条样本记录以下字段：

- `sample_id`
- `model_type`
- `task_type`
- `prompt`
- `output`
- `source_paths`
- `hard_score`
- `llm_score`
- `final_score`
- `llm_reason`

其中 `model_type` 可以统一使用：

- `cybersecurity_eval`
- `teacher_eval`

## 12. 为什么这样设计

本方案相比纯 LLM judge 的好处是：

- 硬性要求由程序直接判断，更稳定
- LLM 只负责它更擅长的语义判断
- 评估流程可以直接落到当前仓库的目录结构上
- 可以同时评 general cybersecurity model 和 teacher-customized model

建议在最终实现中让两部分分数不同权：

- 硬性评估：`30%` 到 `40%`
- LLM 评估：`60%` 到 `70%`

原因是硬性评估主要检查格式和显式要求，而最终质量更多取决于内容契合和来源学习情况。

本方案相比过于复杂的多指标框架也更适合当前阶段，因为当前最重要的是先把评估系统跑起来。

## 13. 结论

本阶段评估方案可以概括为一句话：

先从 prompt 中抽取显式约束和来源定位关键词，对可量化要求进行硬性评估；再结合对应来源材料，由 LLM 对内容契合度、来源学习情况和教学实用性进行辅助评估。

这个方案既适合 general cybersecurity model，也适合 teacher-customized model，并且便于后续继续实现为代码。
