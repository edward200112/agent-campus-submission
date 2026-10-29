# ReAct 执行过程

来源：examples/live-v2/manual_review/trace-1.jsonl

模式：live；实际动作：3 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M05 | 开始审核素材 M05，先读取基础元数据。 | read_material({"section":"base"}) | 读取 base：需人工核实的合成素材；证明资料已提供 | 第 2 步 check_rules({}) |
| 2 / M05 | 基础资料显示正文含"销量第一"待核实表达，需按规则检查。 | check_rules({}) | 审核 needs_review；缺失 无；风险 1 项 | 第 3 步 finish({"outcome":"needs_review"}) |
| 3 / M05 | 规则 R002 判定"销量第一"表述需人工核实，且无补查入口与人工放行入口。 | finish({"outcome":"needs_review"}) | 结束：needs_review；仅处理草稿，未发布 | finish:needs_review |

原始文件 SHA-256：9abe750b56afd032f8c8ad90f6381836cbdd7ea8ad9564c12283f7722875a0d3
