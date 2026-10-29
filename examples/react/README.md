# 从这里阅读 ReAct 过程

这些阅读报告由已提交的真实 DeepSeek Trace 直接生成，原始日志没有修改。每一行并列展示简短依据、工具和参数、工具返回摘要、后续实际动作。next_action 是后续实际记录的关联，不是事后构造的计划。

| 路径 | 阅读报告 | 原始 Trace |
| --- | --- | --- |
| 正常排期 | [normal.md](normal.md) | [原始记录](../live/normal/trace-1.jsonl) |
| 18:00 冲突后建议 19:00 | [conflict.md](conflict.md) | [原始记录](../live/conflict/trace-1.jsonl) |
| 补查后仍缺资料 | [missing.md](missing.md) | [原始记录](../live/missing/trace-1.jsonl) |
| 原版确认重试与文案警告 | [confirmation-original.md](confirmation-original.md) | [原始记录](../live/confirmation/trace-2.jsonl) |
| 保存时突然被占用，重新查时段 | [增强版报告](../live-v2/race_conflict/react-1.md) | [原始记录](../live-v2/race_conflict/trace-1.jsonl) |
| 审核后资料变化，重读并重新审核 | [增强版报告](../live-v2/stale_material/react-1.md) | [原始记录](../live-v2/stale_material/trace-1.jsonl) |
| 瞬时写入失败，有限重试 | [增强版报告](../live-v2/transient_save_failure/react-1.md) | [原始记录](../live-v2/transient_save_failure/trace-1.jsonl) |

可公开的 ReAct 过程是“动作依据 → 动作 → 工具观察 → 下一动作”。这里的依据为模型提供的一句事实摘要，不是模型内部思维过程。

命令行阅读：

```bash
python3 run.py trace --input examples/live/conflict/trace-1.jsonl
```

执行时观察：在 run 或 demo 命令后加入 `--verbose`。历史报告不需要密钥；live 实际执行需要配置 DeepSeek 密钥。
