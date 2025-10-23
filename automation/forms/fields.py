"""Form field metadata for Acuity booking forms."""

from __future__ import annotations

FORM_SELECTORS = {
    'client.firstName': 'input[name="client.firstName"]',
    'client.lastName': 'input[name="client.lastName"]',
    'client.phone': 'input[name="client.phone"]',
    'client.email': 'input[name="client.email"]',
}

REQUIRED_FIELDS = tuple(FORM_SELECTORS.keys())

__all__ = ['FORM_SELECTORS', 'REQUIRED_FIELDS']
