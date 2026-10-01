import os

from django.conf import settings
from django.core.exceptions import ValidationError

# Always rejected, even if an operator lists them in a whitelist env var.
COMPRESSED_EXTENSIONS = frozenset(
    {
        ".zip",
        ".rar",
        ".7z",
        ".gz",
        ".tgz",
        ".tar",
        ".bz2",
        ".tbz2",
        ".xz",
        ".txz",
        ".z",
        ".lz",
        ".lzma",
        ".zst",
        ".cab",
        ".arj",
        ".kmz",
    }
)


def get_allowed_extensions(is_internal: bool = False):
    configured = (
        settings.UPLOAD_ALLOWED_EXTENSIONS_INTERNAL
        if is_internal
        else settings.UPLOAD_ALLOWED_EXTENSIONS_EXTERNAL
    )
    normalised = {"." + e.strip().lower().lstrip(".") for e in configured if e.strip()}
    return normalised - COMPRESSED_EXTENSIONS


def validate_uploaded_file(file_obj, is_internal: bool = False):
    """Raise ValidationError unless the extension is allowed for the given user type."""
    ext = os.path.splitext(getattr(file_obj, "name", "") or "")[1].lower()

    if ext in COMPRESSED_EXTENSIONS:
        raise ValidationError(f"Compressed files ('{ext}') are not allowed.")

    allowed = get_allowed_extensions(is_internal)
    if ext not in allowed:
        raise ValidationError(
            f"File extension '{ext or 'none'}' is not allowed. "
            f"Allowed extensions: {', '.join(sorted(allowed))}."
        )


def is_internal_uploader(request):
    """Same rule as helpers.is_internal(), without its is_staff/user.save() side effect."""
    # Local import: main.models imports this module, and main.helpers is imported by main.models.
    from wildlifelicensing.apps.main.helpers import (
        belongs_to_groups,
        email_in_dbca_domain,
    )

    if not request or not hasattr(request, "user") or not request.user.is_authenticated:
        return False

    return email_in_dbca_domain(request.user.email) and belongs_to_groups(
        request, settings.INTERNAL_GROUPS
    )


def validate_request_files(request):
    internal = is_internal_uploader(request)
    for _key, files in request.FILES.lists():
        for uploaded in files:
            validate_uploaded_file(uploaded, is_internal=internal)
