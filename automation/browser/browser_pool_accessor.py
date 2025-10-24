"""Shared descriptors for accessing nested browser pool attributes."""

from __future__ import annotations

from typing import Any, Optional


class ProxyAttribute:
    """Descriptor that forwards attribute access to a nested object."""

    def __init__(
        self,
        target_attr: str,
        attribute: str,
        *,
        read_only: bool = False,
    ) -> None:
        self._target_attr = target_attr
        self._attribute = attribute
        self._read_only = read_only

    def __get__(self, instance: Any, owner: Optional[type] = None) -> Any:
        if instance is None:
            return self
        target = getattr(instance, self._target_attr, None)
        if target is None:
            return None
        return getattr(target, self._attribute, None)

    def __set__(self, instance: Any, value: Any) -> None:
        if self._read_only:
            raise AttributeError(
                f"Cannot set read-only attribute '{self._attribute}' via proxy."
            )
        target = getattr(instance, self._target_attr, None)
        if target is None:
            raise AttributeError(
                f"Cannot set '{self._attribute}' because '{self._target_attr}' is None."
            )
        setattr(target, self._attribute, value)


def browser_pool_accessor(target_attr: str, *, read_only: bool = False) -> ProxyAttribute:
    """Create a proxy descriptor specifically for ``browser_pool``."""

    return ProxyAttribute(target_attr, "browser_pool", read_only=read_only)


def proxy_attribute(target_attr: str, attribute: str, *, read_only: bool = False) -> ProxyAttribute:
    """Factory for creating general proxy descriptors."""

    return ProxyAttribute(target_attr, attribute, read_only=read_only)
