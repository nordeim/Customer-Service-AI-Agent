from __future__ import annotations

from typing import Any, Dict

from .workflow import WorkflowOrchestrator
from .rules import Rule, ActionDef, Condition


def register_default_workflows(orchestrator: WorkflowOrchestrator) -> None:
    # Example: high-priority escalation workflow
    cond = Condition(operator="AND", conditions=[
        Condition(operator="less_than", field="sentiment.score", value=-0.5),
        Condition(operator="equals", field="customer.tier", value="enterprise"),
    ])
    rule = Rule(
        id="RULE-ESC-001",
        name="High Priority Escalation",
        type="escalation",
        priority=100,
        conditions=cond,
        actions=[
            ActionDef(type="escalate", params={"reason": "Customer request", "priority": "high"}),
            ActionDef(type="sla", params={"target": "15m"}),
        ],
    )
    orchestrator.register_workflow("escalation", [rule])
