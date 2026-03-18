"""Schema Validator — Stdlib-only JSON Schema validation (Draft 2020-12 subset).

Validates JSON data against a schema without any third-party dependencies.
Supports: type, required, properties, enum, pattern, minimum, maximum,
minLength, maxLength, minItems, maxItems, items, additionalProperties,
const, oneOf, anyOf.

Usage:
    from agentic_patterns.schema_validator import validate, ValidationError

    schema = {
        "type": "object",
        "required": ["name", "status"],
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "status": {"type": "string", "enum": ["active", "inactive"]},
        },
    }
    validate({"name": "agent-1", "status": "active"}, schema)  # OK
    validate({"name": ""}, schema)  # Raises ValidationError

Stdlib-only. Zero third-party dependencies.
"""

from __future__ import annotations

import re
from typing import Any


class ValidationError(Exception):
    """Raised when data fails schema validation."""

    def __init__(self, message: str, path: str = ""):
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)


def validate(data: Any, schema: dict[str, Any], path: str = "") -> None:
    """Validate *data* against a JSON Schema dict. Raises ValidationError on failure."""

    # type check
    if "type" in schema:
        _check_type(data, schema["type"], path)

    # const
    if "const" in schema:
        if data != schema["const"]:
            raise ValidationError(f"expected {schema['const']!r}, got {data!r}", path)

    # enum
    if "enum" in schema:
        if data not in schema["enum"]:
            raise ValidationError(f"value {data!r} not in {schema['enum']}", path)

    # numeric constraints
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            raise ValidationError(f"value {data} < minimum {schema['minimum']}", path)
        if "maximum" in schema and data > schema["maximum"]:
            raise ValidationError(f"value {data} > maximum {schema['maximum']}", path)

    # string constraints
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            raise ValidationError(f"string length {len(data)} < minLength {schema['minLength']}", path)
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            raise ValidationError(f"string length {len(data)} > maxLength {schema['maxLength']}", path)
        if "pattern" in schema and not re.search(schema["pattern"], data):
            raise ValidationError(f"string does not match pattern {schema['pattern']!r}", path)

    # array constraints
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            raise ValidationError(f"array length {len(data)} < minItems {schema['minItems']}", path)
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            raise ValidationError(f"array length {len(data)} > maxItems {schema['maxItems']}", path)
        if "items" in schema:
            for i, item in enumerate(data):
                validate(item, schema["items"], f"{path}[{i}]")

    # object constraints
    if isinstance(data, dict):
        if "required" in schema:
            for key in schema["required"]:
                if key not in data:
                    raise ValidationError(f"missing required property '{key}'", path)

        if "properties" in schema:
            for key, prop_schema in schema["properties"].items():
                if key in data:
                    validate(data[key], prop_schema, f"{path}.{key}" if path else key)

        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            extra = set(data.keys()) - allowed
            if extra:
                raise ValidationError(f"additional properties not allowed: {extra}", path)

    # oneOf
    if "oneOf" in schema:
        matches = 0
        for sub in schema["oneOf"]:
            try:
                validate(data, sub, path)
                matches += 1
            except ValidationError:
                pass
        if matches != 1:
            raise ValidationError(f"expected exactly one oneOf match, got {matches}", path)

    # anyOf
    if "anyOf" in schema:
        for sub in schema["anyOf"]:
            try:
                validate(data, sub, path)
                return
            except ValidationError:
                pass
        raise ValidationError("no anyOf schema matched", path)


_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def _check_type(data: Any, expected: str | list[str], path: str) -> None:
    """Check that data matches the expected JSON Schema type(s)."""
    if isinstance(expected, list):
        for t in expected:
            try:
                _check_type(data, t, path)
                return
            except ValidationError:
                pass
        raise ValidationError(f"type {type(data).__name__} not in {expected}", path)

    py_type = _TYPE_MAP.get(expected)
    if py_type is None:
        return  # Unknown type, skip

    if expected == "integer" and isinstance(data, bool):
        raise ValidationError(f"expected integer, got bool", path)
    if expected == "number" and isinstance(data, bool):
        raise ValidationError(f"expected number, got bool", path)

    if not isinstance(data, py_type):
        raise ValidationError(f"expected {expected}, got {type(data).__name__}", path)
