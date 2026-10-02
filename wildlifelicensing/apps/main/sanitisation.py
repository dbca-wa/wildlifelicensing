import html

import nh3
from django.db import models

MAX_PASSES = 5


def sanitise_text(value):
    if "<" not in value and "&" not in value:
        return value
    for _ in range(MAX_PASSES):
        cleaned = html.unescape(nh3.clean(value, tags=set()))
        if cleaned == value:
            return value
        value = cleaned
    # Still changing after MAX_PASSES: give up on the text and drop the angle brackets.
    return value.replace("<", "").replace(">", "")


def sanitise_json(value):
    if isinstance(value, str):
        return sanitise_text(value)
    if isinstance(value, list):
        return [sanitise_json(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitise_json(item) for key, item in value.items()}
    return value


class SanitisationModelMixin:
    def save(self, *args, **kwargs):
        for field in self._meta.concrete_fields:
            if not field.editable or field.choices:
                continue
            value = getattr(self, field.attname)
            if isinstance(field, models.JSONField):
                setattr(self, field.attname, sanitise_json(value))
            elif isinstance(field, (models.CharField, models.TextField)) and isinstance(value, str):
                setattr(self, field.attname, sanitise_text(value))
        super().save(*args, **kwargs)
