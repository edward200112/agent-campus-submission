# ReAct 执行过程

来源：examples/mock-v2/stale_material/trace-1.jsonl

模式：mock；实际动作：9 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M01 | 读取当前素材的基础资料 | read_material({"section":"base"}) | 读取 base：秋日新品预告；证明资料已提供 | 第 2 步 check_rules({}) |
| 2 / M01 | 根据最新读取资料检查规则 | check_rules({}) | 审核 passed；缺失 无；风险 0 项 | 第 3 步 query_slots({"scope":"requested"}) |
| 3 / M01 | 审核通过，检查用户要求的时段 | query_slots({"scope":"requested"}) | 查询 requested；可用 18:00；占用/不可用 无 | 第 4 步 save_draft({"slot":"2026-10-29T18:00:00+08:00"}) |
| 4 / M01 | 保存已查询可用的提案；改时由工具标记待确认 | save_draft({"slot":"2026-10-29T18:00:00+08:00"}) | 失败 STALE_REVIEW：资料或规则变化，必须重新读取和审核 | 第 5 步 read_material({"section":"base"}) |
| 5 / M01 | 工具指出资料或版本已过期，重新读取并审核 | read_material({"section":"base"}) | 读取 base：秋日新品预告（资料已更新）；证明资料已提供 | 第 6 步 check_rules({}) |
| 6 / M01 | 根据最新读取资料检查规则 | check_rules({}) | 审核 passed；缺失 无；风险 0 项 | 第 7 步 query_slots({"scope":"requested"}) |
| 7 / M01 | 审核通过，检查用户要求的时段 | query_slots({"scope":"requested"}) | 查询 requested；可用 18:00；占用/不可用 无 | 第 8 步 save_draft({"slot":"2026-10-29T18:00:00+08:00"}) |
| 8 / M01 | 保存已查询可用的提案；改时由工具标记待确认 | save_draft({"slot":"2026-10-29T18:00:00+08:00"}) | 保存 saved；草稿 D-f911cef91aba；状态 ready；确认 not_required | 第 9 步 finish({"outcome":"draft_ready"}) |
| 9 / M01 | 根据实际保存回执结束；仅保存草稿 | finish({"outcome":"draft_ready"}) | 结束：draft_ready；仅处理草稿，未发布 | finish:draft_ready |

## 外部变更、停止或服务错误

- 第 4 步 / M01：{'kind': 'material_changed_after_review', 'material_id': 'M01', 'version': 2}

原始文件 SHA-256：92900e95294e523999b53a33daaea94f853f56773cbc861907c03a2fe69df8c6
