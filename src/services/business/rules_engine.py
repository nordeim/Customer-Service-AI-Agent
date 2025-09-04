from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .rules import Rule
from .conditions import evaluate
from .actions import execute_action, ActionContext


@dataclass
class RuleEvaluationResult:
    matched_rules: List[str]
    actions_executed: List[Dict[str, Any]]
    requires_escalation: bool = False
    escalation_reason: Optional[str] = None
    routing_decision: Optional[Dict[str, Any]] = None
    sla: Optional[Dict[str, Any]] = None


class RulesEngine:
    def __init__(self, rules: List[Rule], services: Dict[str, Any]):
        self.rules = [r for r in rules if r.enabled]
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self.ax = ActionContext(services)

    async def evaluate(self, context: Dict[str, Any]) -> RuleEvaluationResult:
        matched: List[str] = []
        actions_executed: List[Dict[str, Any]] = []
        requires_escalation = False
        escalation_reason: Optional[str] = None
        sla_obj: Optional[Dict[str, Any]] = None

        for rule in self.rules:
            cond = rule.conditions
            if cond is None or evaluate(cond, context):
                matched.append(rule.id)
                for action in rule.actions:
                    result = await execute_action({"type": action.type, "params": action.params}, context, self.ax)
                    actions_executed.append({"rule": rule.id, "action": action.type, "result": result})
                    if action.type == "escalate":
                        requires_escalation = True
                        escalation_reason = action.params.get("reason")
                    if action.type == "sla":
                        sla_obj = result

        return RuleEvaluationResult(
            matched_rules=matched,
            actions_executed=actions_executed,
            requires_escalation=requires_escalation,
            escalation_reason=escalation_reason,
            sla=sla_obj,
        )
