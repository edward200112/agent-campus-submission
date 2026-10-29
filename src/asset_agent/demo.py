"""Executable acceptance fixtures. Every artifact is produced by an actual run."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from .agent import run_request
from .domain import DomainError, TZ
from .model import DeepSeekModel, MockModel
from .storage import Store
from .trace_view import read_view, render_markdown

CASES = ["normal", "missing", "risk", "conflict", "duplicate", "save_failure",
         "changed_occupancy", "supplement", "manual_review", "no_slots", "batch",
         "confirmation", "confirmation_conflict", "step_limit", "tool_limit",
         "race_conflict", "stale_material", "transient_save_failure"]


def request_for(case, material="M01"):
    return {"request_id": f"demo-{case}-001", "timezone": "Asia/Shanghai", "items": [
        {"material_id": material, "channel": "wechat", "requested_at": "2026-10-29T18:00:00+08:00", "requirement_type": "hard"}]}


def schedules_for(hour):
    return [{"channel": "wechat", "slot": f"2026-10-29T{hour:02d}:00:00+08:00", "owner": f"synthetic-existing-{hour}"}]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def verify(case, outputs, snapshots, extra):
    first = outputs[0]["items"][0]
    if case not in {"step_limit", "tool_limit"}:
        check(all(o["run_status"] != "incomplete" for o in outputs), "模型未完成本用例")
    check(all(not o["published"] and all(not x["published"] for x in o["items"]) for o in outputs), "不得发布")
    if case in {"normal", "supplement", "stale_material", "transient_save_failure"}:
        check(first["outcome"] == "draft_ready" and first["scheduled_at"] == first["requested_at"], "应保存原要求时段")
    elif case == "missing":
        check(first["outcome"] == "needs_info" and "rights_proof" in first["missing_fields"], "应指出缺少证明")
        check(snapshots[0]["draft_count"] == 0, "缺资料不应生成可执行草稿")
    elif case in {"risk", "manual_review"}:
        check(first["outcome"] == ("blocked" if case == "risk" else "needs_review"), "风险处理状态错误")
        check(first["risk_reasons"] and snapshots[0]["draft_count"] == 0, "风险必须留证且不可排期")
    elif case in {"conflict", "changed_occupancy", "confirmation", "confirmation_conflict", "race_conflict"}:
        check(first["outcome"] == "needs_confirmation" and first["suggested_at"].endswith("19:00:00+08:00"), "18 点冲突应建议最近的 19 点并待确认")
        check(first["scheduled_at"] is None and first["requested_at"].endswith("18:00:00+08:00"), "不得擅自改写硬性要求")
        check(snapshots[0]["draft_count"] == 1 and snapshots[0]["draft_claim_count"] == 0, "待确认提案不应占正式时段")
        if case == "changed_occupancy":
            second = outputs[1]["items"][0]
            check(second["outcome"] == "draft_ready" and second["scheduled_at"].endswith("18:00:00+08:00"), "占用变化后应重新查询")
            check(second["draft"]["record"]["id"] == first["draft"]["record"]["id"] and snapshots[1]["draft_count"] == 1, "更新同一草稿，不能新增")
        elif case == "confirmation":
            check(extra["confirmation"]["state"] == "ready", "用户确认后应可排期")
            check(outputs[1]["items"][0]["confirmation_status"] == "confirmed", "重复执行应保留真实确认")
        elif case == "confirmation_conflict":
            check(extra["confirmation_error"] == "SLOT_CONFLICT", "确认时必须复查时段")
    elif case == "duplicate":
        second = outputs[1]["items"][0]
        check(first["draft"]["record"]["id"] == second["draft"]["record"]["id"], "重复保存必须同一 ID")
        check(first["draft"]["record"]["revision"] == second["draft"]["record"]["revision"], "无变化不应生成新版本")
        check(snapshots[-1]["draft_count"] == 1 and second["draft"]["save_status"] == "existing", "重复提交只保存一份")
    elif case == "save_failure":
        check(first["outcome"] == "failed" and first["draft"]["save_status"] == "failed", "保存失败必须明确报告")
        check(snapshots[0]["draft_count"] == snapshots[0]["draft_claim_count"] == snapshots[0]["event_count"] == 0, "失败必须回滚草稿、占位和事件")
    elif case == "no_slots":
        check(first["outcome"] == "unavailable" and snapshots[0]["draft_count"] == 0, "无时段不得伪造排期")
    elif case == "batch":
        items = outputs[0]["items"]
        check(len({i["suggested_at"] for i in items}) == 2, "同批次提案不能互相冲突")
    elif case in {"step_limit", "tool_limit"}:
        check(outputs[0]["run_status"] == "incomplete" and outputs[0]["stop_reasons"], "超限必须明确未完成")


def database_snapshot(store):
    drafts = [store.get_id(row[0]) for row in store.conn.execute("SELECT id FROM drafts ORDER BY id")]
    return {"draft_count": len(drafts), "drafts": drafts,
            "draft_claim_count": store.conn.execute("SELECT count(*) FROM slot_claims WHERE source='draft'").fetchone()[0],
            "event_count": store.conn.execute("SELECT count(*) FROM draft_events").fetchone()[0],
            "slot_claims": [dict(row) for row in store.conn.execute("SELECT * FROM slot_claims ORDER BY channel,slot")]}


def run_case(case, mode, out, data_dir, on_event=None):
    material = {"missing": "M02", "risk": "M03", "supplement": "M04", "manual_review": "M05"}.get(case, "M01")
    request = request_for(case, material)
    if case == "batch":
        request["items"].append({**request["items"][0], "material_id": "M06"})
    schedules = schedules_for(18) if case in {"conflict", "changed_occupancy", "confirmation", "confirmation_conflict", "batch"} else []
    if case == "no_slots":
        schedules = [entry for hour in range(9, 21) for entry in schedules_for(hour)]
    write(out / "schedules-before.json", schedules)
    write(out / "case.json", {"case": case, "mode": mode, "save_failures": -1 if case == "save_failure" else 0})
    outputs, snapshots, extra = [], [], {}
    with tempfile.TemporaryDirectory(prefix="material-agent-demo-") as temp:
        if case == "stale_material":
            # Mutate a private fixture copy, never the submitted source catalog.
            local_data = Path(temp) / "data"
            shutil.copytree(data_dir, local_data)
            data_dir = local_data
        store = Store(Path(temp) / "agent.sqlite", schedules)
        try:
            changed_once = False
            def before_tool(action, args, tools):
                nonlocal changed_once
                if changed_once or action != "save_draft" or not isinstance(args, dict):
                    return None
                changed_once = True
                if case == "race_conflict":
                    changed = [{"channel": tools.item["channel"], "slot": args["slot"], "owner": "synthetic-race-competitor"}]
                    store.replace_schedules(changed)
                    write(out / "external-change.json", {"kind": "slot_taken_after_query", "schedules": changed})
                    return {"kind": "slot_taken_after_query", "slot": args["slot"], "note": "工具执行前发生合成占用变化，模型将从保存失败观察到冲突"}
                if case == "stale_material":
                    path = data_dir / "materials.json"
                    catalog = json.loads(path.read_text(encoding="utf-8"))
                    catalog["M01"]["version"] += 1
                    catalog["M01"]["title"] += "（资料已更新）"
                    write(path, catalog)
                    write(out / "materials-after.json", catalog)
                    return {"kind": "material_changed_after_review", "material_id": "M01", "version": 2}
                return None
            count = 2 if case in {"duplicate", "changed_occupancy", "confirmation"} else 1
            for index in range(count):
                if index == 1 and case == "changed_occupancy":
                    changed = schedules_for(19)
                    store.replace_schedules(changed)
                    write(out / "schedules-after.json", changed)
                if index == 1 and case == "confirmation":
                    draft = outputs[0]["items"][0]["draft"]["record"]
                    extra["confirmation"] = store.confirm(draft["id"], draft["revision"], draft["suggested_at"], data_dir)
                    write(out / "user-confirmation.json", {"source": "simulated_user_cli_in_acceptance_fixture", "draft": extra["confirmation"], "published": False})
                write(out / f"input-{index + 1}.json", request)
                model = MockModel() if mode == "mock" else DeepSeekModel()
                result, events = run_request(request, model, store, data_dir,
                    max_steps=2 if case == "step_limit" else 60,
                    max_tool_calls=2 if case == "tool_limit" else 50,
                    save_failures=-1 if case == "save_failure" else (1 if case == "transient_save_failure" else 0),
                    trace_path=out / f"trace-{index + 1}.jsonl", on_event=on_event,
                    before_tool=before_tool if case in {"race_conflict", "stale_material"} else None)
                outputs.append(result)
                snapshots.append(database_snapshot(store))
                write(out / f"output-{index + 1}.json", result)
                write(out / f"database-{index + 1}.json", snapshots[-1])
                view = read_view(out / f"trace-{index + 1}.jsonl")
                write(out / f"react-{index + 1}.json", view)
                (out / f"react-{index + 1}.md").write_text(render_markdown(view), encoding="utf-8")
            if case == "confirmation_conflict":
                store.replace_schedules(schedules_for(19))
                draft = outputs[0]["items"][0]["draft"]["record"]
                try:
                    store.confirm(draft["id"], draft["revision"], draft["suggested_at"], data_dir)
                    extra["confirmation_error"] = None
                except DomainError as exc:
                    extra["confirmation_error"] = exc.code
                write(out / "confirmation-attempt.json", {**extra, "source": "simulated_user_cli_in_acceptance_fixture", "published": False})
            try:
                verify(case, outputs, snapshots, extra)
                if case in {"race_conflict", "stale_material", "transient_save_failure"}:
                    code = {"race_conflict": "SLOT_CONFLICT", "stale_material": "STALE_REVIEW", "transient_save_failure": "SAVE_FAILED"}[case]
                    failed = next((i for i, event in enumerate(events) if event.get("observation", {}).get("code") == code), None)
                    check(failed is not None, "故障必须实际发生并记录")
                    later = [event["action"] for event in events[failed + 1:] if event.get("event") == "action"]
                    if case == "race_conflict":
                        check("query_slots" in later and later.index("query_slots") < later.index("save_draft"), "模型需重新查时段后保存")
                    elif case == "stale_material":
                        check("read_material" in later and "check_rules" in later and "save_draft" in later, "模型需重读并重新审核后保存")
                    else:
                        check("save_draft" in later, "瞬时失败后模型需决定再次保存")
                verification = {"passed": True}
            except (AssertionError, ValueError) as exc:
                verification = {"passed": False, "error": str(exc)}
            write(out / "verification.json", verification)
            return {"case": case, **verification, "runs": len(outputs),
                    "steps": sum(o["steps"] for o in outputs), "mode": mode}
        finally:
            store.close()


def run_demo(mode, selected, out, data_dir, on_event=None):
    cases = CASES if selected == "all" else selected.split(",")
    if not cases or set(cases) - set(CASES):
        raise DomainError("UNKNOWN_CASE", "用例名称不支持")
    out = out or Path("runtime") / ("demo-" + mode + "-" + datetime.now(TZ).strftime("%Y%m%d-%H%M%S"))
    if out.exists() and any(out.iterdir()):
        raise DomainError("OUTPUT_EXISTS", "输出目录非空，请换一个目录以保留原始证据")
    out.mkdir(parents=True, exist_ok=True)
    if mode == "live":
        DeepSeekModel()  # Fail before emitting any misleading 'live' case artifacts.
    results = []
    for case in cases:
        result = run_case(case, mode, out / case, data_dir, on_event=on_event)
        results.append(result)
        print(json.dumps({"case_completed": case, "passed": result["passed"], "mode": mode}, ensure_ascii=False), flush=True)
    report = {"passed": all(r["passed"] for r in results), "mode": mode,
              "case_count": len(results), "run_count": sum(r["runs"] for r in results),
              "cases": results, "output_dir": str(out),
              "boundary": "Mock 仅验证流程，不证明真实模型决策效果" if mode == "mock" else "实际 DeepSeek 工具调用；业务资料、工具和用户确认均为本地合成场景"}
    write(out / "report.json", report)
    return report
