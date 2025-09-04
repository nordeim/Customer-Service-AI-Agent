from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from src.services.business.workflow import WorkflowOrchestrator
from src.services.business.workflows import register_default_workflows
from src.services.business.escalation import EscalationService
from src.services.business.sla import SLAService


async def main() -> None:
    # Mock services
    services = {
        "escalation_service": EscalationService(None),  # mock SF client
        "sla_service": SLAService(),
    }

    # Setup orchestrator and register workflows
    orchestrator = WorkflowOrchestrator(services)
    register_default_workflows(orchestrator)

    # Sample context: negative sentiment + enterprise customer
    context = {
        "sentiment": {"score": -0.7},
        "customer": {"tier": "enterprise"},
        "channel": "web",
        "message": "I'm very frustrated with this issue!",
        "issue": {"summary": "Product not working as expected"},
    }

    # Run escalation workflow
    result = await orchestrator.run("escalation", context)

    print("Workflow Result:")
    print(f"  Matched rules: {result.matched_rules}")
    print(f"  Actions executed: {len(result.actions_executed)}")
    print(f"  Requires escalation: {result.requires_escalation}")
    print(f"  Escalation reason: {result.escalation_reason}")
    if result.sla:
        print(f"  SLA deadline: {result.sla.get('deadline')}")

    # Show action details
    for action in result.actions_executed:
        print(f"  - Rule {action['rule']}: {action['action']} -> {action['result']}")


if __name__ == "__main__":
    asyncio.run(main())
