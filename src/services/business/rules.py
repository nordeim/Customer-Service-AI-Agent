from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # optional dependency


@dataclass
class Condition:
    operator: str
    conditions: Optional[List["Condition"]] = None
    field: Optional[str] = None
    value: Any = None


@dataclass
class ActionDef:
    type: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    id: str
    name: str
    type: str
    priority: int = 0
    enabled: bool = True
    conditions: Condition | Dict[str, Any] | None = None
    actions: List[ActionDef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def _parse_condition(obj: Dict[str, Any]) -> Condition:
    op = obj.get("operator") or obj.get("op") or "AND"
    if "conditions" in obj:
        return Condition(
            operator=op,
            conditions=[_parse_condition(c) for c in obj.get("conditions", [])],
        )
    return Condition(operator=op, field=obj.get("field"), value=obj.get("value"))


def _parse_action(obj: Dict[str, Any]) -> ActionDef:
    return ActionDef(type=obj.get("type"), params=obj.get("params", {}))


def parse_rule(obj: Dict[str, Any]) -> Rule:
    conditions = obj.get("conditions")
    cond = _parse_condition(conditions) if isinstance(conditions, dict) else None
    actions = [_parse_action(a) for a in obj.get("actions", [])]
    return Rule(
        id=obj.get("id"),
        name=obj.get("name", obj.get("id", "rule")),
        type=obj.get("type", "automation"),
        priority=int(obj.get("priority", 0)),
        enabled=bool(obj.get("enabled", True)),
        conditions=cond,
        actions=actions,
        metadata=obj.get("metadata", {}),
    )


def parse_rules_from_json(json_obj: List[Dict[str, Any]]) -> List[Rule]:
    return [parse_rule(item) for item in json_obj]


def parse_rules_from_yaml(text: str) -> List[Rule]:  # pragma: no cover
    if yaml is None:
        raise RuntimeError("pyyaml not installed")
    data = yaml.safe_load(text)
    if not isinstance(data, list):
        raise ValueError("YAML rules must be a list")
    return parse_rules_from_json(data)
