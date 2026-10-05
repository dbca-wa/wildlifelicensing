# Production Migration Plan: Legacy Media to Private Media (TASK 19094)

Runbook for copying legacy uploaded files from `MEDIA_ROOT` to `PRIVATE_MEDIA_ROOT` with the management command `move_media_to_private`. Design and rationale: [.github/plans/task-19094-move-media-to-private.md](../.github/plans/task-19094-move-media-to-private.md).

## 1. Summary

| Item | Value |
|------|-------|
| Command | `python manage.py move_media_to_private [--perform]` |
| Default mode | **DRY-RUN** (no filesystem writes). Files are copied only with `--perform`. |
| Scope | Files referenced by `Document.file`. The source path is `MEDIA_ROOT/<name>`, the target path is `PRIVATE_MEDIA_ROOT/<name>` (same relative name). |
| Operation | **Copy only.** Files in `MEDIA_ROOT` are never modified or deleted. Existing targets are never overwritten. |
| Database | No writes, no migrations. `Document.file.name` values do not change. |
| Idempotent | Yes. Safe to re-run, for example after an interruption. |
| Downtime | Not required (the application falls back to `MEDIA_ROOT` for files not yet copied). A maintenance window is optional, pending approval. |

### Per-row outcomes

| Outcome | Meaning | Summary bucket |
|---------|---------|----------------|
| `WOULD_MIGRATE` / `MIGRATED` | Source exists, target absent. Dry-run / `--perform`. | Migrated |
| `EXISTS` | Target already present (a post-TASK 19095 upload, or an identical copy). | Already exists / Skipped |
| `SKIPPED` | Another row already referenced the same file name in this run. | Already exists / Skipped |
| `MISSING` | Empty file name, or the file is in neither root. | Missing / Not found |
| `ERROR` | Path escapes the root, target exists with different content, or an I/O error occurred. | Errors |

Where output goes:
- **`stdout`**: every row plus the summary. Lines look like `[PERFORM] [ 12/4810] MIGRATED      pk=12 2019/03/04/licence.pdf`.
- **`logs/wildlifelicensing.log`** (INFO and above): the start line, `WOULD_MIGRATE` / `MIGRATED`, `MISSING`, `ERROR` and the summary. `EXISTS` and `SKIPPED` rows are logged at DEBUG only, so they reach the console (`stderr`) but not the rotating log file.
- **`stderr`**: the console log handler echoes all log lines, including DEBUG.

The exit status is non-zero when the summary reports one or more errors.

## 2. Conventions

- Run all commands **inside the application container, as user `oim`, in `/app`**, with the same environment (`.env`, `PRIVATE_MEDIA_ROOT`, `MEDIA_ROOT`) as the running application. Running as another user (for example `root`) creates files with the wrong owner.
- Placeholders in `<angle brackets>` are filled in by Operations.
- Set these shell variables once per session. They resolve the real paths from Django settings:

```bash
cd /app
export MEDIA_ROOT_DIR="$(python manage.py shell --no-imports -c 'from django.conf import settings; print(settings.MEDIA_ROOT)' 2>/dev/null | tail -n 1)"
export PRIVATE_MEDIA_ROOT="$(python manage.py shell --no-imports -c 'from django.conf import settings; print(settings.PRIVATE_MEDIA_ROOT)' 2>/dev/null | tail -n 1)"
export BACKUP_DIR="<backup directory outside the container filesystem>"
export TS="$(date +%Y%m%d_%H%M)"   # one timestamp for the whole session
echo "MEDIA_ROOT=$MEDIA_ROOT_DIR"; echo "PRIVATE_MEDIA_ROOT=$PRIVATE_MEDIA_ROOT"
```

Both echoed paths must be non-empty absolute paths before continuing.

## 3. Step 0 - Preconditions (go/no-go)

All items must be ticked. Any unticked item is a **no-go**.

- [ ] TASK 19095 and TASK 19098 are deployed: `python manage.py showmigrations main` shows `0052` and `0053` applied.
- [ ] The release containing the `move_media_to_private` command is deployed. No migrations are involved.
- [ ] `MEDIA_ROOT` and `PRIVATE_MEDIA_ROOT` are different directories and neither is inside the other (the command refuses to run otherwise).
- [ ] `PRIVATE_MEDIA_ROOT` is on **persistent storage** that is shared by every application replica and survives redeploys. The Dockerfile declares no volume, so confirm that one is mounted at this path. Files that are uploaded or copied to a non-persistent path are lost on the next deploy.
- [ ] `PRIVATE_MEDIA_ROOT` is **not** served directly by the reverse proxy or web server.
- [ ] Free space on the `PRIVATE_MEDIA_ROOT` volume is at least the size of the referenced legacy files plus the agreed margin (confirmed again in Step 3).
- [ ] The command is run as user `oim`: `id -un` prints `oim`.
- [ ] The change or maintenance window is approved, and an approver is named for the Step 3 sign-off: `<approver>`.

## 4. Step 1 - Pre-deployment backup

1. Record sizes, free space and file counts (keep this output; it is the baseline for Step 5):

```bash
du -sh "$MEDIA_ROOT_DIR" "$PRIVATE_MEDIA_ROOT"
df -h "$PRIVATE_MEDIA_ROOT"
find "$MEDIA_ROOT_DIR" -type f | wc -l
find "$PRIVATE_MEDIA_ROOT" -type f | wc -l
```

2. Back up **both** directories. A volume snapshot is preferred. Otherwise create archives outside the container filesystem:

```bash
tar -czf "$BACKUP_DIR/media_$TS.tar.gz" -C "$MEDIA_ROOT_DIR" .
tar -czf "$BACKUP_DIR/private-media_$TS.tar.gz" -C "$PRIVATE_MEDIA_ROOT" .
```

3. Verify that each archive is readable and contains every file. The archive file count must equal the `find` count from step 1 (`grep -v '/$'` drops directory entries):

```bash
tar -tzf "$BACKUP_DIR/media_$TS.tar.gz" | grep -vc '/$'
tar -tzf "$BACKUP_DIR/private-media_$TS.tar.gz" | grep -vc '/$'
```

4. A database backup is not required by this command (it performs no database writes). Follow the standard pre-change policy if it requires one.

## 5. Step 2 - Dry-run

```bash
DRY_OUT="logs/move_media_to_private_dryrun_$TS.out"
python manage.py move_media_to_private > "$DRY_OUT" 2> "logs/move_media_to_private_dryrun_$TS.err"
echo "exit=$?"
tail -n 12 "$DRY_OUT"
```

Confirm that nothing was written:

```bash
find "$PRIVATE_MEDIA_ROOT" -type f | wc -l            # must equal the Step 1 value
find "$PRIVATE_MEDIA_ROOT" -name '*.partial' | wc -l  # must be 0
```

A non-zero `exit` is expected when the summary reports errors. Review them in Step 3.

## 6. Step 3 - Review dry-run results (go/no-go)

```bash
grep -E '\] ERROR +pk=' "$DRY_OUT"     # every line must be explained
grep -E '\] MISSING +pk=' "$DRY_OUT"   # review with the business owner
```

- [ ] **Errors** is 0, or every `ERROR` line is explained and accepted. Typical causes: `target exists with different content - not overwritten` (two different files with the same name, see Open Item #5 in the task plan), `path escapes media root`, or a permission error.
- [ ] **Missing / Not found** is reviewed. These rows are already broken today (their files are in neither root). They are reported to the business owner and do not block the migration.
- [ ] **Bytes to copy** is below **Free space on target** with the agreed safety margin.
- [ ] The summary adds up: `Total Document rows = Migrated + Already exists / Skipped + Missing / Not found + Errors`.
- [ ] `MEDIA_ROOT` and `PRIVATE_MEDIA_ROOT` in the summary header match the values from Step 1.
- [ ] Sign-off recorded by `<approver>` with the dry-run summary attached.

A dry-run cannot detect unreadable source files. Those appear as `WOULD_MIGRATE` and only fail as `ERROR` during Step 4.

## 7. Step 4 - Production execution (`--perform`)

Run inside `tmux` or `screen`, or as a one-off job, so that a dropped session does not interrupt it.

```bash
OUT="logs/move_media_to_private_perform_$TS.out"
python manage.py move_media_to_private --perform > "$OUT" 2> "logs/move_media_to_private_perform_$TS.err"
echo "exit=$?"
tail -n 12 "$OUT"
```

- The application can stay online. New uploads already go to `PRIVATE_MEDIA_ROOT`, and `getPrivateFile` falls back to `MEDIA_ROOT` for files that are not copied yet.
- If the run is interrupted, re-run the same command. Files that are already copied are reported as `EXISTS`, and a truncated file can never exist under a final name (each file is copied to `<name>.partial` and renamed after a size check). Use a new output file name for each run (a new `TS`).
- A non-zero exit means one or more `ERROR` rows. Other files were still copied. Review them with `grep -E '\] ERROR +pk=' "$OUT"`, fix the cause and re-run.
- **Keep every `--perform` `.out` file.** They are the authoritative list of `MIGRATED` paths for rollback (section 9).

## 8. Step 5 - Post-migration verification

1. **Zero dry-run re-run.** Run the dry-run again. Every source/target pair is compared byte-for-byte:

```bash
VERIFY_OUT="logs/move_media_to_private_verify_$TS.out"
python manage.py move_media_to_private > "$VERIFY_OUT" 2>/dev/null
tail -n 12 "$VERIFY_OUT"
```

   Expected: `Migrated (would migrate): 0`. `Missing / Not found` and `Errors` equal the values accepted in Step 3.

2. **File counts.** The private count must equal the Step 1 private count plus the `Migrated` value of the `--perform` summary (sum the values if several runs were needed):

```bash
find "$PRIVATE_MEDIA_ROOT" -type f | wc -l
find "$PRIVATE_MEDIA_ROOT" -name '*.partial' | wc -l      # must be 0
find "$MEDIA_ROOT_DIR" -type f | wc -l                    # must equal the Step 1 value (sources untouched)
```

3. **Ownership.** Nothing is owned by another user:

```bash
find "$PRIVATE_MEDIA_ROOT" ! -user oim | head
```

4. **Storage API check (Django shell).** This is the access path that previously raised `FileNotFoundError`:

```python
from django.core.exceptions import SuspiciousFileOperation
from wildlifelicensing.apps.main.models import Document

storage = Document._meta.get_field("file").storage
missing, suspicious = [], []
for pk, name in Document.objects.exclude(file="").values_list("pk", "file").iterator():
    try:
        if not storage.exists(name):
            missing.append(pk)
    except SuspiciousFileOperation:
        suspicious.append(pk)
print(len(missing), len(suspicious))
```

   Expected: `len(missing)` equals the Step 3 `Missing / Not found` count minus rows with an empty file name, and `len(suspicious)` equals the number of `path escapes media root` errors accepted in Step 3.

5. **UI spot checks.** As an owner customer and as an officer, open three legacy documents (an application attachment, a licence PDF and a communications log attachment). Each must return 200 with the correct content. As a different customer, the same links must return 403. Re-send a legacy licence email or email a legacy attachment, then confirm there is no new `FileNotFoundError`:

```bash
grep -c "FileNotFoundError" logs/wildlifelicensing.log
```

6. `MEDIA_ROOT` stays untouched. Deleting source files is **not** part of this runbook. It needs a separate approval (Open Item #1 in the task plan).

## 9. Rollback Strategy

The command performs no database writes and never modifies or deletes source files. Rollback only concerns the files it created in `PRIVATE_MEDIA_ROOT`.

| Situation | Action |
|-----------|--------|
| Dry-run only | Nothing to roll back. |
| `--perform` stopped part-way or reported errors | No rollback needed. Fix the cause and re-run (idempotent). Leftover partial files are safe to remove: `find "$PRIVATE_MEDIA_ROOT" -name '*.partial' -type f -delete` |
| Migrated files must be withdrawn (wrong owner, wrong volume, corrupted copies) | Delete **only** the paths reported as `MIGRATED`, using the procedure below. Files uploaded after TASK 19095 are never in that list and must not be touched. The application keeps serving the documents from `MEDIA_ROOT` through the existing fallback. |
| Private volume damaged or lost | Restore `PRIVATE_MEDIA_ROOT` from the Step 1 backup, then re-run the command. |
| The command code must be withdrawn | Revert the commit. Nothing else imports the command. |

### Withdrawing migrated files

`OUT` must be the output of **every** `--perform` run. If the migration needed more than one run, combine the files first, because a re-run reports earlier copies as `EXISTS`, not `MIGRATED`:

```bash
cat logs/move_media_to_private_perform_*.out > /tmp/perform_all.out
OUT=/tmp/perform_all.out
```

Extract the migrated paths. The `sed` expression keeps everything after `pk=<id> `, so file names that contain spaces stay intact:

```bash
grep -E '\] MIGRATED +pk=[0-9]+ ' "$OUT" | sed -E 's/.*\] MIGRATED +pk=[0-9]+ //' > /tmp/migrated_paths.txt
wc -l /tmp/migrated_paths.txt     # must equal the total "Migrated" count of the --perform summaries
head /tmp/migrated_paths.txt      # review the list before deleting anything
```

Delete them (paths are relative to `PRIVATE_MEDIA_ROOT`; `--` protects names that begin with `-`):

```bash
cd "$PRIVATE_MEDIA_ROOT" && xargs -d '\n' -a /tmp/migrated_paths.txt rm -v --
```

Empty date directories left behind are harmless. Remove the temporary files afterwards: `rm -f /tmp/perform_all.out /tmp/migrated_paths.txt`.

### After a rollback, verify

- [ ] `find "$MEDIA_ROOT_DIR" -type f | wc -l` equals the Step 1 value.
- [ ] `find "$PRIVATE_MEDIA_ROOT" -type f | wc -l` equals the Step 1 value for `PRIVATE_MEDIA_ROOT`.
- [ ] Legacy document links still open for the owner and for officers (served from `MEDIA_ROOT` by the fallback).
- [ ] Reading a legacy `Document` file through the Storage API (email attachments) fails again, as it did before the migration. This is the expected pre-migration state.

If source files are deleted later (a separate, approved task), rolling back that step needs the Step 1 `MEDIA_ROOT` backup. Keep the backup until that task is complete and verified.

## 10. Follow-ups (not part of this runbook)

- Decide whether and when to delete the source files in `MEDIA_ROOT`, and handle files no `Document` row references (task plan Open Items #1 and #2).
- After that, remove the `MEDIA_ROOT` fallback from `getPrivateFile` and the `^media/` route from `wildlifelicensing/urls.py` (task plan Open Item #8).
