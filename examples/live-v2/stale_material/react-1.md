# ReAct 执行过程

来源：examples/live-v2/stale_material/trace-1.jsonl

模式：live；实际动作：9 步。

只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程

| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |
| --- | --- | --- | --- | --- |
| 1 / M01 | 开始审核素材 M01，先读取基础元数据。 | read_material({"section":"base"}) | 读取 base：秋日新品预告；证明资料已提供 | 第 2 步 check_rules({}) |
| 2 / M01 | 基础资料已读取，渠道在允许范围内，现检查内部规则。 | check_rules({}) | 审核 passed；缺失 无；风险 0 项 | 第 3 步 query_slots({"scope":"requested"}) |
| 3 / M01 | 审核已通过，查询 requested 时段 2026-10-29T18:00+08:00 的可用性。 | query_slots({"scope":"requested"}) | 查询 requested；可用 18:00；占用/不可用 无 | 第 4 步 save_draft({"slot":"2026-10-29T18:00:00+08:00"}) |
| 4 / M01 | requested 时段可用且审核通过，保存该时段草稿。 | save_draft({"slot":"2026-10-29T18:00:00+08:00"}) | 失败 STALE_REVIEW：资料或规则变化，必须重新读取和审核 | 第 5 步 read_material({"section":"base"}) |
| 5 / M01 | 保存返回 STALE_REVIEW，需重新读取基础资料。 | read_material({"section":"base"}) | 读取 base：秋日新品预告（资料已更新）；证明资料已提供 | 第 6 步 check_rules({}) |
| 6 / M01 | 资料已更新至 version 2，重新检查内部规则。 | check_rules({}) | 审核 passed；缺失 无；风险 0 项 | 第 7 步 query_slots({"scope":"requested"}) |
| 7 / M01 | 重新审核通过，重新查询 requested 时段可用性。 | query_slots({"scope":"requested"}) | 查询 requested；可用 18:00；占用/不可用 无 | 第 8 步 save_draft({"slot":"2026-10-29T18:00:00+08:00"}) |
| 8 / M01 | 基于 version 2 重新审核通过且 requested 时段可用，重新保存草稿。 | save_draft({"slot":"2026-10-29T18:00:00+08:00"}) | 保存 saved；草稿 D-e8c8a53eb95a；状态 ready；确认 not_required | 第 9 步 finish({"outcome":"draft_ready"}) |
| 9 / M01 | 草稿已保存为 ready，confirmation_status=not_required，时段为 requested 的 2026-10-29T18:00+08:00。 | finish({"outcome":"draft_ready"}) | 结束：draft_ready；仅处理草稿，未发布 | finish:draft_ready |

## 外部变更、停止或服务错误

- 第 4 步 / M01：{'kind': 'material_changed_after_review', 'material_id': 'M01', 'version': 2}

原始文件 SHA-256：0f35e5b248e94962f30c0a85e1a1813c2d625f6de39e1f7f9ab7f9c5d613cf49
