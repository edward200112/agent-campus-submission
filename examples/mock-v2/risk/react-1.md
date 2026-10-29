# ReAct 执行过程

来源：examples/mock-v2/risk/trace-1.jsonl

模式：mock；实际动作：3 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M03 | 读取当前素材的基础资料 | read_material({"section":"base"}) | 读取 base：命中内部禁止表达；证明资料已提供 | 第 2 步 check_rules({}) |
| 2 / M03 | 根据最新读取资料检查规则 | check_rules({}) | 审核 blocked；缺失 无；风险 1 项 | 第 3 步 finish({"outcome":"blocked"}) |
| 3 / M03 | 规则检查结果不允许自动排期 | finish({"outcome":"blocked"}) | 结束：blocked；仅处理草稿，未发布 | finish:blocked |

原始文件 SHA-256：8ad5d9b0dcae54242e9b6928d2991e798c15a3e8eab4ad405a0d6bf4032ab77f
