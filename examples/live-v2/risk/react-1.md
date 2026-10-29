# ReAct 执行过程

来源：examples/live-v2/risk/trace-1.jsonl

模式：live；实际动作：3 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M03 | 开始审核素材 M03，先读取基础元数据。 | read_material({"section":"base"}) | 读取 base：命中内部禁止表达；证明资料已提供 | 第 2 步 check_rules({}) |
| 2 / M03 | 基础资料显示正文含内部禁用词，需按规则检查。 | check_rules({}) | 审核 blocked；缺失 无；风险 1 项 | 第 3 步 finish({"outcome":"blocked"}) |
| 3 / M03 | 规则检查命中 R001 阻断项（正文含“保证收益”），且无补查入口。 | finish({"outcome":"blocked"}) | 结束：blocked；仅处理草稿，未发布 | finish:blocked |

原始文件 SHA-256：5d6d179f78cf5eb1c52ff38b396cc5e779e9b7243deb7578bcbc464fe66e8a3c
