# ReAct 阅读入口与 Agent 增强

## 如何看到过程

优先打开 [可读报告索引](../examples/react/README.md)，尤其是 [冲突报告](../examples/react/conflict.md)。原始 JSONL 中步骤、工具参数、返回观察和简短依据都在同一行；下一行是模型随后选择的动作。阅读器把后续实际动作关联为显式 next_action，方便评审逐行比较。

`python3 run.py trace --input 路径` 导出 Markdown；`--format json` 导出结构化阅读视图；`--output` 保存报告。该入口不调用模型，不改变原始文件，包含原始文件 SHA-256。单次执行使用 `run --verbose`，逐步日志到 stderr、最终结构化 JSON 到 stdout。

报告不是内部思维过程。reason/decision_summary 是模型公开给出的简短动作依据；不存在补写或展示完整思维链。

## 本轮实现的增强

1. 增加独立 Trace 阅读器：步骤、依据、参数、观察摘要、后续动作、停止原因、来源模式和完整性哈希。批次阅读不会把其他素材的动作连作后续动作。
2. 每个工具观察增加 runtime.state 和 runtime.budget。前者报告实际审核/保存/确认状态，后者报告剩余全局决策、工具调用和单素材步数；这些字段不代替模型选择动作。
3. 增加 on_event 运行回调与 --verbose；原始记录还包含真实 tool_call_id，方便关联服务响应。
4. 明确冲突和资料过期的重新规划：保存时新冲突要求重新查询后选择；审核后资料变化要求重读、重新审核再保存。最多两次保存尝试及原有全局上限仍生效。
5. 结束前明确核对 confirmed / not_required / pending_confirmation，避免将已确认草稿再次称为待确认。历史模型文案不重写；阅读器对“事实 confirmed、理由却称待确认”标注警告。

## 新增验收场景

| 场景 | 环境变化 | 必须出现的动作调整 |
| --- | --- | --- |
| race_conflict | 查询 18:00 空闲后，首次保存前合成占用该槽位 | 保存返回 SLOT_CONFLICT → 模型重新查询 → 保存替代提案，等待确认 |
| stale_material | 规则通过后，首次保存前更新合成素材版本和标题 | 保存返回 STALE_REVIEW → 模型重读 → 重新审核 → 再查询与保存 |
| transient_save_failure | 首次事务写入后、提交前注入失败，下一次写入恢复 | 保存返回 SAVE_FAILED → 模型决定有限重试 → 成功回执后结束 |

故障注入由 demo 的可信本地夹具完成，不暴露给模型。external_change 是夹具实际改变环境的审计事件，不是伪造模型动作。stale_material 使用临时资料副本，不修改提交的 data/materials.json。

对新场景的断言不仅检查最终状态，也检查 Trace 中确实出现错误，以及错误之后的查询/重读/审核动作。Mock 只验证流程，真实 DeepSeek 证据另存 live-v2。

## 证据

- 原版 15 组真实验收：[live/report.json](../examples/live/report.json)，原始文件保留。
- 增强版实际结果：[live-v2/report.json](../examples/live-v2/report.json)。
- 增强版离线结果：[mock-v2/report.json](../examples/mock-v2/report.json)。
- 本轮自动测试：[test-results-v2.txt](../examples/test-results-v2.txt)。

实际通过数量与失败情况以这些运行产物及评估文档的增强版记录为准，不将预期结果写成已经通过。

## 继续扩展的边界

优先方向是版本化资料库、更多模型回归和精细化时段区间。当前没有为此增加真实发布权限、多用户鉴权或线上部署。模型仍无确认和发布工具，所有替代时段仍须用户独立确认。
