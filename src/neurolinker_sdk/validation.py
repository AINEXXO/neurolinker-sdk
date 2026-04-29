from __future__ import annotations

from typing import Any, Dict, List, Type, Union

from pydantic import BaseModel, TypeAdapter, ValidationError

from .errors import NeuroLinkerConfigError

Schema = Union[Type[BaseModel], TypeAdapter]


def _schema_label(schema: Schema) -> str:
    if isinstance(schema, TypeAdapter):
        return repr(schema)
    return schema.__name__


def normalize_pydantic(
    value: Any,
    schema: Schema,
    *,
    label: str,
) -> Dict[str, Any]:
    """Validate ``value`` against ``schema`` and return a serialised dict.

    ``schema`` may be a ``BaseModel`` subclass or a ``TypeAdapter`` (for ``Union`` /
    ``Annotated`` types like ``ChunkingConfig``). ``BaseModel`` instances are dumped
    directly; dicts are validated through ``schema``.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True)
    if isinstance(value, dict):
        try:
            validated = (
                schema.validate_python(value)
                if isinstance(schema, TypeAdapter)
                else schema.model_validate(value)
            )
        except ValidationError as exc:
            raise NeuroLinkerConfigError(f"Invalid {label}: {exc}") from exc
        return validated.model_dump(exclude_none=True)
    raise NeuroLinkerConfigError(
        f"{label} must be a {_schema_label(schema)} instance or a dict. "
        f"Got: {type(value).__name__}"
    )


def normalize_pydantic_list(
    values: Any,
    schema: Type[BaseModel],
    *,
    label: str,
    allow_empty: bool = False,
) -> List[Dict[str, Any]]:
    """Validate each item in ``values`` against ``schema`` and return a list of dicts."""
    if not isinstance(values, list):
        raise NeuroLinkerConfigError(f"{label} must be a list.")
    if not values and not allow_empty:
        raise NeuroLinkerConfigError(f"{label} must be a non-empty list.")
    return [
        normalize_pydantic(item, schema, label=f"{label}[{idx}]")
        for idx, item in enumerate(values)
    ]
