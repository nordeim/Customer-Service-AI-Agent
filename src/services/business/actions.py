from __future__ import annotations

from typing import Any, Dict


class ActionContext:
    def __init__(self, services: Dict[str, Any]):
        self.services = services

    def get(self, key: str) -> Any:
        return self.services.get(key)


async def execute_action(action: Dict[str, Any], context: Dict[str, Any], ax: ActionContext) -> Dict[str, Any]:
    a_type = action.get("type")
    params = action.get("params", {})

    if a_type == "escalate":
        esc = ax.get("escalation_service")
        return await esc.escalate(context, params)

    if a_type == "notify":
        notif = ax.get("notification_service")
        return await notif.send(context, params)

    if a_type == "sla":
        sla = ax.get("sla_service")
        return await sla.apply(context, params)

    if a_type == "webhook":
        wh = ax.get("webhook_service")
        return await wh.call(context, params)

    if a_type == "set_field":
        # simple mutation into context
        path = params.get("field")
        value = params.get("value")
        if path:
            context[path] = value
        return {"status": "ok"}

    return {"status": "skipped", "reason": f"unknown action {a_type}"}
