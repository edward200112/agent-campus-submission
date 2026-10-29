# ReAct 执行过程

来源：examples/live-v2/missing/trace-1.jsonl

模式：live；实际动作：4 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M02 | 开始审核素材 M02，先读取基础元数据。 | read_material({"section":"base"}) | 读取 base：缺少授权资料的合成素材；证明资料缺失 | 第 2 步 read_material({"section":"supplementary"}) |
| 2 / M02 | 基础资料显示 rights_status 为 unknown 且可补查，先补查证明资料。 | read_material({"section":"supplementary"}) | 读取 supplementary：缺少授权资料的合成素材；证明资料缺失 | 第 3 步 check_rules({}) |
| 3 / M02 | 补查后 rights_proof 仍为空、rights_status 仍为 unknown，需按规则检查。 | check_rules({}) | 审核 needs_info；缺失 rights_proof；风险 0 项 | 第 4 步 finish({"outcome":"needs_info"}) |
| 4 / M02 | 补查后仍缺 rights_proof，规则判定 needs_info，需用户补充授权资料。 | finish({"outcome":"needs_info"}) | 结束：needs_info；仅处理草稿，未发布 | finish:needs_info |

原始文件 SHA-256：b01a9995bec3a9674b1ded6cc3e0090e6d5ac9373f6502f36d2365248dcc6f58
