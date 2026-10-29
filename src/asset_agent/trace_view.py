"""Read-only ReAct views derived from actual JSONL events, without model calls."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from .domain import DomainError, canonical


def observation_summary(event):
    if event.get("event") != "action":
        return str(event.get("reason") or event.get("error") or event.get("change") or event.get("event"))
    obs = event.get("observation", {})
    if not obs.get("ok"):
        return f"失败 {obs.get('code', 'UNKNOWN')}：{obs.get('message', '')}"
    action = event.get("action")
    if action == "read_material":
        material = obs.get("material")
        return "素材不存在" if material is None else f"读取 {obs.get('section')}：{material.get('title', '')}；证明资料{'已提供' if material.get('rights_proof') else '缺失'}"
    if action == "check_rules":
        return f"审核 {obs.get('status')}；缺失 {', '.join(obs.get('missing_fields', [])) or '无'}；风险 {len(obs.get('reasons', []))} 项"
    if action == "query_slots":
        slots = obs.get("slots", [])
        available = obs.get("ranked_available_slots") or [s["slot"] for s in slots if s["available"]]
        occupied = [s["slot"] for s in slots if not s["available"]]
        def times(values):
            return ", ".join(s[11:16] for s in values[:4]) + ("…" if len(values) > 4 else "") if values else "无"
        return f"查询 {obs.get('scope')}；可用 {times(available)}；占用/不可用 {times(occupied)}"
    if action == "save_draft":
        draft = obs.get("draft", {})
        return f"保存 {obs.get('save_status')}；草稿 {draft.get('id')}；状态 {draft.get('state')}；确认 {draft.get('confirmation_status')}"
    if action == "finish":
        return f"结束：{obs.get('outcome')}；仅处理草稿，未发布"
    return canonical(obs)


def load_trace(path: Path):
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise DomainError("INVALID_TRACE", f"Trace 第 {number} 行不是有效 JSON") from exc
        if not isinstance(event, dict) or event.get("event") not in {"action", "stopped", "model_error", "external_change"}:
            raise DomainError("INVALID_TRACE", f"Trace 第 {number} 行事件类型不支持")
        if event["event"] == "action":
            valid = (isinstance(event.get("step"), int) and event["step"] > 0
                     and isinstance(event.get("material_id"), str)
                     and isinstance(event.get("action"), str)
                     and isinstance(event.get("arguments"), (dict, type(None)))
                     and isinstance(event.get("observation"), dict)
                     and isinstance(event.get("decision_summary"), str))
            if not valid:
                raise DomainError("INVALID_TRACE", f"Trace 第 {number} 行动作记录不完整")
        events.append({**event, "source_line": number})
    if not events:
        raise DomainError("EMPTY_TRACE", "Trace 没有事件")
    return events


def build_view(events, source="", source_sha256=None):
    rows, warnings = [], []
    for index, event in enumerate(events):
        if event.get("event") != "action":
            continue
        follow = next((x for x in events[index + 1:] if x.get("material_id") == event.get("material_id")
                       and x.get("event") in {"action", "stopped", "model_error"}), None)
        next_action = None
        if follow and follow["event"] == "action":
            next_action = {"step": follow["step"], "action": follow["action"],
                           "arguments": follow.get("arguments"), "decision_summary": follow.get("decision_summary", "")}
        obs = event["observation"]
        if event.get("action") == "finish" and obs.get("ok"):
            termination = "finish:" + obs.get("outcome", "unknown")
        elif follow and follow["event"] != "action":
            termination = str(follow.get("reason") or follow.get("error"))
        else:
            termination = None
        # This is an audit annotation, never a rewrite of the model's reason.
        reason = event.get("decision_summary", "")
        state = obs.get("runtime", {}).get("state", {})
        if not state:
            prior = [x for x in events[:index + 1] if x.get("material_id") == event.get("material_id") and x.get("action") == "save_draft" and x.get("observation", {}).get("ok")]
            state = prior[-1]["observation"].get("draft", {}) if prior else {}
        if state.get("confirmation_status") == "confirmed" and "待确认" in reason:
            warnings.append({"step": event.get("step"), "message": "模型依据出现“待确认”，但工具事实为 confirmed；保留原文，以结构化事实为准"})
        rows.append({"step": event["step"], "source_line": event.get("source_line", index + 1),
                     "material_id": event.get("material_id"), "decision_summary": reason,
                     "action": event["action"], "arguments": event.get("arguments"),
                     "observation_summary": observation_summary(event), "observation": obs,
                     "next_action": next_action, "termination": termination,
                     "provider": event.get("provider", {})})
    modes = sorted({e.get("provider", {}).get("mode") or e.get("mode") or "unknown" for e in events})
    return {"source": source, "source_sha256": source_sha256, "modes": modes,
            "note": "只根据原始 Trace 生成视图；next_action 来自同一素材后续实际动作，不是补写的计划；reason 是公开简短依据，不是内部思维过程",
            "action_count": len(rows), "steps": rows,
            "other_events": [e for e in events if e.get("event") != "action"], "warnings": warnings}


def read_view(path):
    return build_view(load_trace(path), str(path), hashlib.sha256(path.read_bytes()).hexdigest())


def cell(value):
    text = value if isinstance(value, str) else canonical(value)
    return html.escape(text, quote=False).replace("|", "\\|").replace("\n", " ").replace("`", "&#96;")


def render_markdown(view):
    lines = ["# ReAct 执行过程", "", f"来源：{cell(view['source'])}", "",
             f"模式：{', '.join(view['modes'])}；实际动作：{view['action_count']} 步。", "", view["note"], "",
             "| 步骤 / 素材 | 简短决策依据 | 动作与参数 | 工具返回摘要 | 后续实际动作 |",
             "| --- | --- | --- | --- | --- |"]
    for row in view["steps"]:
        args = {k: v for k, v in (row.get("arguments") or {}).items() if k != "reason"}
        follow = row["next_action"]
        if follow:
            params = {k: v for k, v in (follow.get("arguments") or {}).items() if k != "reason"}
            next_text = f"第 {follow['step']} 步 {follow['action']}({canonical(params)})"
        else:
            next_text = row["termination"] or "记录中没有后续动作（可能为截断记录）"
        lines.append("| " + " | ".join(cell(v) for v in [f"{row['step']} / {row['material_id']}", row["decision_summary"],
                     row["action"] + "(" + canonical(args) + ")", row["observation_summary"], next_text]) + " |")
    if view["other_events"]:
        lines.extend(["", "## 外部变更、停止或服务错误", ""])
        for event in view["other_events"]:
            lines.append(f"- 第 {event.get('step')} 步 / {cell(event.get('material_id'))}：{cell(observation_summary(event))}")
    if view["warnings"]:
        lines.extend(["", "## 原始记录中的文案不一致", ""])
        lines.extend(f"- 第 {w['step']} 步：{w['message']}。" for w in view["warnings"])
    if view.get("source_sha256"):
        lines.extend(["", "原始文件 SHA-256：" + view["source_sha256"]])
    return "\n".join(lines) + "\n"


def format_event(event):
    if event.get("event") == "action":
        args = {k: v for k, v in (event.get("arguments") or {}).items() if k != "reason"}
        return (f"[{event['step']}] {event['material_id']} {event['action']}({canonical(args)})\n"
                f"  依据：{event.get('decision_summary', '')}\n  观察：{observation_summary(event)}")
    return f"[{event.get('step')}] {event.get('material_id')} {event.get('event')}：{observation_summary(event)}"
