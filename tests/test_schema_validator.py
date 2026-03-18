"""Tests for schema validator."""

import pytest
from agentic_patterns.schema_validator import ValidationError, validate


class TestTypeValidation:
    def test_string(self):
        validate("hello", {"type": "string"})

    def test_integer(self):
        validate(42, {"type": "integer"})

    def test_boolean(self):
        validate(True, {"type": "boolean"})

    def test_array(self):
        validate([1, 2], {"type": "array"})

    def test_object(self):
        validate({"a": 1}, {"type": "object"})

    def test_null(self):
        validate(None, {"type": "null"})

    def test_wrong_type(self):
        with pytest.raises(ValidationError):
            validate(42, {"type": "string"})

    def test_bool_not_integer(self):
        with pytest.raises(ValidationError):
            validate(True, {"type": "integer"})

    def test_union_type(self):
        validate("hi", {"type": ["string", "null"]})
        validate(None, {"type": ["string", "null"]})


class TestStringConstraints:
    def test_min_length(self):
        validate("ab", {"type": "string", "minLength": 2})
        with pytest.raises(ValidationError):
            validate("a", {"type": "string", "minLength": 2})

    def test_max_length(self):
        validate("ab", {"type": "string", "maxLength": 3})
        with pytest.raises(ValidationError):
            validate("abcd", {"type": "string", "maxLength": 3})

    def test_pattern(self):
        validate("abc123", {"type": "string", "pattern": "^[a-z]+[0-9]+$"})
        with pytest.raises(ValidationError):
            validate("ABC", {"type": "string", "pattern": "^[a-z]+$"})


class TestNumericConstraints:
    def test_minimum(self):
        validate(5, {"type": "integer", "minimum": 0})
        with pytest.raises(ValidationError):
            validate(-1, {"type": "integer", "minimum": 0})

    def test_maximum(self):
        validate(5, {"type": "integer", "maximum": 10})
        with pytest.raises(ValidationError):
            validate(11, {"type": "integer", "maximum": 10})


class TestObjectConstraints:
    def test_required(self):
        validate({"name": "x"}, {"type": "object", "required": ["name"]})
        with pytest.raises(ValidationError, match="missing required"):
            validate({}, {"type": "object", "required": ["name"]})

    def test_additional_properties_false(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        validate({"name": "x"}, schema)
        with pytest.raises(ValidationError, match="additional properties"):
            validate({"name": "x", "extra": 1}, schema)

    def test_nested_properties(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "count": {"type": "integer", "minimum": 0},
            },
        }
        validate({"name": "x", "count": 5}, schema)
        with pytest.raises(ValidationError):
            validate({"name": "", "count": 5}, schema)


class TestArrayConstraints:
    def test_min_items(self):
        with pytest.raises(ValidationError):
            validate([], {"type": "array", "minItems": 1})

    def test_max_items(self):
        with pytest.raises(ValidationError):
            validate([1, 2, 3], {"type": "array", "maxItems": 2})

    def test_items_schema(self):
        validate([1, 2], {"type": "array", "items": {"type": "integer"}})
        with pytest.raises(ValidationError):
            validate([1, "x"], {"type": "array", "items": {"type": "integer"}})


class TestEnumAndConst:
    def test_enum(self):
        validate("a", {"enum": ["a", "b", "c"]})
        with pytest.raises(ValidationError):
            validate("d", {"enum": ["a", "b", "c"]})

    def test_const(self):
        validate(42, {"const": 42})
        with pytest.raises(ValidationError):
            validate(43, {"const": 42})


class TestComposition:
    def test_one_of(self):
        schema = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
        validate("hi", schema)
        validate(42, schema)
        with pytest.raises(ValidationError):
            validate(True, schema)  # bool matches neither

    def test_any_of(self):
        schema = {"anyOf": [{"type": "string", "minLength": 3}, {"type": "integer"}]}
        validate("abc", schema)
        validate(42, schema)
        with pytest.raises(ValidationError):
            validate("ab", schema)  # string too short, not integer
