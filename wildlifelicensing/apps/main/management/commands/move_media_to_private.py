import filecmp
import logging
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import filesizeformat

from wildlifelicensing.apps.main.models import Document

logger = logging.getLogger(__name__)


def safe_join(root, relative_path):
    # Absolute path of relative_path under root, or None if it escapes root
    root = os.path.realpath(root)
    try:
        candidate = os.path.realpath(os.path.join(root, relative_path))
        if os.path.commonpath([root, candidate]) != root:
            return None
    except ValueError:
        return None
    return candidate


class Command(BaseCommand):
    help = (
        "Copy files referenced by Document rows from MEDIA_ROOT to "
        "PRIVATE_MEDIA_ROOT. Dry-run unless --perform is given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--perform",
            action="store_true",
            default=False,
            help="Actually copy files. Without this flag nothing is written.",
        )

    def handle(self, *args, **options):
        media_root = os.path.realpath(settings.MEDIA_ROOT)
        private_root = os.path.realpath(settings.PRIVATE_MEDIA_ROOT)
        # Equal or nested roots would make the copy meaningless or leave
        # "private" files inside the legacy media directory
        if os.path.commonpath([media_root, private_root]) in (media_root, private_root):
            raise CommandError(
                f"MEDIA_ROOT ({media_root}) and PRIVATE_MEDIA_ROOT ({private_root}) "
                "must not be equal or nested."
            )

        is_dry_run = not options["perform"]
        mode_tag = "[DRY-RUN]" if is_dry_run else "[PERFORM]"
        verbosity = options["verbosity"]

        rows = Document.objects.order_by("pk").values_list("pk", "file")
        total = rows.count()
        width = len(str(total))
        counts = {"migrated": 0, "skipped": 0, "missing": 0, "errors": 0}
        bytes_to_copy = 0
        processed_names = set()

        logger.info(
            f"{mode_tag} Start {__name__}: MEDIA_ROOT={media_root} "
            f"PRIVATE_MEDIA_ROOT={private_root} rows={total}"
        )

        for index, (pk, name) in enumerate(rows.iterator(), start=1):
            bucket, outcome, detail, level = self.process_row(
                name, media_root, private_root, is_dry_run, processed_names
            )
            counts[bucket] += 1
            if outcome in ("WOULD_MIGRATE", "MIGRATED"):
                bytes_to_copy += detail
                detail = ""

            line = f"{mode_tag} [{index:>{width}}/{total}] {outcome:<13} pk={pk} {name}"
            if detail:
                line += f" - {detail}"
            logger.log(level, line)
            if verbosity >= 1:
                self.stdout.write(line)

        self.print_summary(
            mode_tag, is_dry_run, media_root, private_root, total, counts, bytes_to_copy
        )

        if counts["errors"]:
            raise CommandError(
                f"{counts['errors']} error(s) occurred during migration - see log"
            )

    def process_row(self, name, media_root, private_root, is_dry_run, processed_names):
        """Return (summary bucket, outcome, detail, log level) for one Document row.

        For WOULD_MIGRATE / MIGRATED the detail is the file size in bytes.
        """
        if not name:
            return "missing", "MISSING", "empty file name", logging.WARNING
        if name in processed_names:
            return "skipped", "SKIPPED", "duplicate reference", logging.INFO
        processed_names.add(name)

        source = safe_join(media_root, name)
        target = safe_join(private_root, name)
        if source is None or target is None:
            return "errors", "ERROR", "path escapes media root", logging.ERROR

        temp_file = target + ".partial"
        try:
            source_exists = os.path.isfile(source)
            if os.path.isfile(target):
                if not source_exists:
                    return (
                        "skipped",
                        "EXISTS",
                        "already in private media",
                        logging.INFO,
                    )
                if filecmp.cmp(source, target, shallow=False):
                    return (
                        "skipped",
                        "EXISTS",
                        "identical copy already in private media",
                        logging.INFO,
                    )
                return (
                    "errors",
                    "ERROR",
                    "target exists with different content - not overwritten",
                    logging.ERROR,
                )
            if not source_exists:
                return (
                    "missing",
                    "MISSING",
                    "not found in MEDIA_ROOT or PRIVATE_MEDIA_ROOT",
                    logging.WARNING,
                )

            size = os.path.getsize(source)
            if is_dry_run:
                return "migrated", "WOULD_MIGRATE", size, logging.INFO

            # Copy to a temporary name first so an interrupted run never leaves
            # a truncated file under the final name
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(source, temp_file)
            if os.path.getsize(temp_file) != size:
                raise OSError("copied file size differs from source")
            os.replace(temp_file, target)
            return "migrated", "MIGRATED", size, logging.INFO
        except (OSError, ValueError) as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    logger.error(f"Could not remove temporary file {temp_file}")
            return "errors", "ERROR", str(e), logging.ERROR

    def print_summary(
        self, mode_tag, is_dry_run, media_root, private_root, total, counts, bytes_to_copy
    ):
        mode = "DRY-RUN" if is_dry_run else "PERFORM"
        migrated_label = "Migrated (would migrate)" if is_dry_run else "Migrated"
        free_space = shutil.disk_usage(private_root).free
        summary = [
            f"==== move_media_to_private summary ({mode}) ====",
            f"MEDIA_ROOT:               {media_root}",
            f"PRIVATE_MEDIA_ROOT:       {private_root}",
            f"Total Document rows:      {total}",
            f"{migrated_label + ':':<25} {counts['migrated']}",
            f"Already exists / Skipped: {counts['skipped']}",
            f"Missing / Not found:      {counts['missing']}",
            f"Errors:                   {counts['errors']}",
            f"Bytes to copy:            {filesizeformat(bytes_to_copy)} ({bytes_to_copy} bytes)",
            f"Free space on target:     {filesizeformat(free_space)}",
        ]
        if is_dry_run:
            summary.append("Re-run with --perform to copy files.")
        for line in summary:
            logger.info(f"{mode_tag} {line}")
            self.stdout.write(line)
