# ReAct 执行过程

来源：examples/live-v2/changed_occupancy/trace-2.jsonl

模式：live；实际动作：5 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M01 | 开始处理素材 M01，先读取基础元数据。 | read_material({"section":"base"}) | 读取 base：秋日新品预告；证明资料已提供 | 第 2 步 check_rules({}) |
| 2 / M01 | 基础资料已读取，渠道 wechat 在允许列表内，现检查内部规则。 | check_rules({}) | 审核 passed；缺失 无；风险 0 项 | 第 3 步 query_slots({"scope":"requested"}) |
| 3 / M01 | 审核已通过，查询 requested 时段 2026-10-29T18:00+08:00 的可用性。 | query_slots({"scope":"requested"}) | 查询 requested；可用 18:00；占用/不可用 无 | 第 4 步 save_draft({"slot":"2026-10-29T18:00:00+08:00"}) |
| 4 / M01 | requested 时段 18:00 可用，按原始要求保存草稿。 | save_draft({"slot":"2026-10-29T18:00:00+08:00"}) | 保存 saved；草稿 D-59d3034beb5c；状态 ready；确认 not_required | 第 5 步 finish({"outcome":"draft_ready"}) |
| 5 / M01 | 审核通过，requested 时段 18:00 可用，草稿已保存且 confirmation_status=not_required、state=ready。 | finish({"outcome":"draft_ready"}) | 结束：draft_ready；仅处理草稿，未发布 | finish:draft_ready |

原始文件 SHA-256：b561adfe9e221cb92e9eed7f57bb52504f627735b228dbd442f02cf19be10dc9
