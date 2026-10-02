from django.core.serializers import serialize
from django.db.models.query import QuerySet

try:
    from django.utils import simplejson as json
except ImportError:
    import json

from django.template import Library
from django.utils.safestring import mark_safe

from ..serializers import WildlifeLicensingJSONEncoder

register = Library()

# Escapes that keep serialised JSON from closing an inline <script> block.
_SCRIPT_UNSAFE = {
    ord("<"): "\\u003C",
    ord(">"): "\\u003E",
    ord("&"): "\\u0026",
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}


@register.filter
def jsonify(obj):
    if isinstance(obj, QuerySet):
        data = serialize("json", obj)
    else:
        data = json.dumps(obj, cls=WildlifeLicensingJSONEncoder)
    return mark_safe(data.translate(_SCRIPT_UNSAFE))
