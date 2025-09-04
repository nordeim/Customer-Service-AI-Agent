from __future__ import annotations

from typing import Any, Dict, List

from .rules_engine import RulesEngine, RuleEvaluationResult
from .rules import Rule


class WorkflowOrchestrator:
    def __init__(self, services: Dict[str, Any]):
        self.services = services
        self.workflows: Dict[str, List[Rule]] = {}

    def register_workflow(self, name: str, rules: List[Rule]) -> None:
        self.workflows[name] = rules

    async def run(self, name: str, context: Dict[str, Any]) -> RuleEvaluationResult:
        rules = self.workflows.get(name, [])
        engine = RulesEngine(rules, self.services)
        return await engine.evaluate(context)
