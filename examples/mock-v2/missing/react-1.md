# ReAct 执行过程

来源：examples/mock-v2/missing/trace-1.jsonl

模式：mock；实际动作：5 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M02 | 读取当前素材的基础资料 | read_material({"section":"base"}) | 读取 base：缺少授权资料的合成素材；证明资料缺失 | 第 2 步 check_rules({}) |
| 2 / M02 | 根据最新读取资料检查规则 | check_rules({}) | 审核 needs_info；缺失 rights_proof；风险 0 项 | 第 3 步 read_material({"section":"supplementary"}) |
| 3 / M02 | 缺失证明，补查资料后重新审核 | read_material({"section":"supplementary"}) | 读取 supplementary：缺少授权资料的合成素材；证明资料缺失 | 第 4 步 check_rules({}) |
| 4 / M02 | 根据最新读取资料检查规则 | check_rules({}) | 审核 needs_info；缺失 rights_proof；风险 0 项 | 第 5 步 finish({"outcome":"needs_info"}) |
| 5 / M02 | 补查后仍缺必要资料，等待用户补充 | finish({"outcome":"needs_info"}) | 结束：needs_info；仅处理草稿，未发布 | finish:needs_info |

原始文件 SHA-256：b893f10525eb82bebb15b056b962251bbf245ceb4029712195313763243a6e65
