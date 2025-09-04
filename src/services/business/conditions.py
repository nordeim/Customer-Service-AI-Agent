from __future__ import annotations

import re
from typing import Any, Dict, List

from .rules import Condition


def get_nested(context: Dict[str, Any], path: str) -> Any:
    cur: Any = context
    for key in path.split('.'):
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return None
    return cur


def eval_single(condition: Condition, context: Dict[str, Any]) -> bool:
    field = condition.field or ""
    value = condition.value
    current = get_nested(context, field) if field else None
    ops = {
        "equals": lambda x, y: x == y,
        "not_equals": lambda x, y: x != y,
        "greater_than": lambda x, y: x > y,
        "less_than": lambda x, y: x < y,
        "contains": lambda x, y: (y in x) if hasattr(x, '__contains__') else False,
        "not_contains": lambda x, y: (y not in x) if hasattr(x, '__contains__') else True,
        "in": lambda x, y: x in (y or []),
        "not_in": lambda x, y: x not in (y or []),
        "regex": lambda x, y: bool(re.match(str(y or ''), str(x or ''))),
        "truthy": lambda x, _: bool(x),
        "falsy": lambda x, _: not bool(x),
    }
    fn = ops.get(condition.operator, lambda *_: False)
    return fn(current, value)


def evaluate(condition: Condition, context: Dict[str, Any]) -> bool:
    op = (condition.operator or "AND").upper()
    if op in ("AND", "OR"):
        children: List[Condition] = condition.conditions or []
        results = [evaluate(c, context) for c in children]
        return all(results) if op == "AND" else any(results)
    if op == "NOT":
        child = (condition.conditions or [Condition(operator="truthy", field="__missing__")])[0]
        return not evaluate(child, context)
    return eval_single(condition, context)
