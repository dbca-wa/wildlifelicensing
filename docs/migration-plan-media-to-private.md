# Production Migration Plan: Legacy Media to Private Media (TASK 19094)

Runbook for copying legacy uploaded files from `MEDIA_ROOT` to `PRIVATE_MEDIA_ROOT` with `python manage.py move_media_to_private`. Design, output format and edge cases: [.github/plans/task-19094-move-media-to-private.md](../.github/plans/task-19094-move-media-to-private.md).

**What the command does**
- Copies the file of every `Document` row from `MEDIA_ROOT/<name>` to `PRIVATE_MEDIA_ROOT/<name>`.
- **Dry-run by default.** It writes files only with `--perform`.
- **Copy only.** It never modifies or deletes source files, never overwrites a target, and never writes to the database.
- **Safe to re-run** (for example after an interruption). Already copied files are reported as `EXISTS`.
- **No downtime needed.** The application falls back to `MEDIA_ROOT` for files not copied yet.
- Exit status is non-zero when the summary reports errors.

## Quick version

One-time check before the first run: `PRIVATE_MEDIA_ROOT` is on persistent storage (see step 2).

1. Open a shell in the application container (do not switch to `root`). `id -un` prints `oim`. `cd /app`.
2. `python manage.py move_media_to_private` - dry-run. Read the summary at the end: **Errors** should be 0.
3. `python manage.py move_media_to_private --perform` - copies the files. Keep the output (save it to a file).
4. `python manage.py move_media_to_private` - check. The summary shows `Migrated (would migrate): 0`.

The sections below are the full procedure: what to check, what to record, and how to roll back.

## 1. Setup

Run everything **inside the application container, as user `oim`, in `/app`**, with the same `.env` as the running application. Another user (for example `root`) creates files with the wrong owner.

```bash
cd /app
export MEDIA_ROOT_DIR="$(python manage.py shell --no-imports -c 'from django.conf import settings; print(settings.MEDIA_ROOT)' 2>/dev/null | tail -n 1)"
export PRIVATE_MEDIA_ROOT="$(python manage.py shell --no-imports -c 'from django.conf import settings; print(settings.PRIVATE_MEDIA_ROOT)' 2>/dev/null | tail -n 1)"
export TS="$(date +%Y%m%d_%H%M)"
echo "MEDIA_ROOT=$MEDIA_ROOT_DIR"; echo "PRIVATE_MEDIA_ROOT=$PRIVATE_MEDIA_ROOT"; id -un
```

Both paths must be non-empty absolute paths, and `id -un` must print `oim`.

## 2. Preconditions (all required)

- [ ] TASK 19095 and 19098 are deployed: `python manage.py showmigrations main` shows `0052` and `0053` applied.
- [ ] `PRIVATE_MEDIA_ROOT` is on **persistent storage** shared by all replicas (the Dockerfile declares no volume; confirm one is mounted). Otherwise copied files are lost on the next deploy.
- [ ] `PRIVATE_MEDIA_ROOT` is **not** served directly by the reverse proxy or web server.
- [ ] `MEDIA_ROOT` and `PRIVATE_MEDIA_ROOT` are different directories, neither inside the other.
- [ ] A recent scheduled backup or snapshot of the media volumes exists. Record its date: `<backup date>`. (The command never modifies or deletes existing files, so no extra backup is taken.)
- [ ] The change window is approved. Approver for the go/no-go in step 4: `<approver>`.

## 3. Baseline

```bash
du -sh "$MEDIA_ROOT_DIR" "$PRIVATE_MEDIA_ROOT"; df -h "$PRIVATE_MEDIA_ROOT"
find "$MEDIA_ROOT_DIR" -type f | wc -l        # baseline A
find "$PRIVATE_MEDIA_ROOT" -type f | wc -l    # baseline B
```

## 4. Dry-run and go/no-go

```bash
DRY_OUT="logs/move_media_to_private_dryrun_$TS.out"
python manage.py move_media_to_private > "$DRY_OUT" 2> "${DRY_OUT%.out}.err"; echo "exit=$?"
tail -n 12 "$DRY_OUT"                          # summary
grep -E '\] (ERROR|MISSING) +pk=' "$DRY_OUT"   # rows to review
find "$PRIVATE_MEDIA_ROOT" -type f | wc -l     # still = B (nothing written)
```

Go only if all are true, and the approver has signed off with the summary attached:
- [ ] **Errors** is 0, or every `ERROR` line is explained and accepted (for example `target exists with different content`).
- [ ] **Missing** rows are reported to the business owner. They are already broken today and do not block.
- [ ] **Bytes to copy** is below **Free space on target** with the agreed margin.
- [ ] The paths in the summary header match step 1.

## 5. Run (`--perform`)

Run inside `tmux`/`screen` or as a one-off job.

```bash
OUT="logs/move_media_to_private_perform_$TS.out"
python manage.py move_media_to_private --perform > "$OUT" 2> "${OUT%.out}.err"; echo "exit=$?"
tail -n 12 "$OUT"
grep -E '\] ERROR +pk=' "$OUT"
```

- Interrupted, or errors to fix? Fix the cause, set a new `TS`, and run the same commands again.
- **Keep every `--perform` `.out` file.** It is the only list of copied files for rollback.

## 6. Verify

```bash
python manage.py move_media_to_private 2>/dev/null | tail -n 12   # Migrated (would migrate): 0
find "$PRIVATE_MEDIA_ROOT" -type f | wc -l            # = B + total Migrated of all --perform runs
find "$PRIVATE_MEDIA_ROOT" -name '*.partial' | wc -l  # 0
find "$MEDIA_ROOT_DIR" -type f | wc -l                # = A (sources untouched)
find "$PRIVATE_MEDIA_ROOT" ! -user oim | head         # no output
```

In the browser, open three legacy documents (an application attachment, a licence PDF, a communications log attachment):
- [ ] As the owner customer and as an officer: they open (200).
- [ ] As a different customer: 403.
- [ ] Re-send a legacy licence email. `grep -c FileNotFoundError logs/wildlifelicensing.log` does not increase.

Do **not** delete anything from `MEDIA_ROOT`. That is a separate, approved task.

## 7. Rollback

No database changes and no source files are touched, so rollback only concerns copied files.

| Situation | Action |
|-----------|--------|
| Dry-run only, or `--perform` stopped part-way | Nothing to undo. Re-run when fixed. Leftover `*.partial` files can be deleted. |
| Copied files must be withdrawn (wrong owner, wrong volume, corrupted) | Delete only the `MIGRATED` paths (below). The application keeps serving from `MEDIA_ROOT`. |
| Private volume damaged | Restore `PRIVATE_MEDIA_ROOT` from the scheduled backup, then re-run. |

Withdraw copied files (combine **all** `--perform` outputs, because a re-run reports earlier copies as `EXISTS`):

```bash
cat logs/move_media_to_private_perform_*.out \
  | grep -E '\] MIGRATED +pk=[0-9]+ ' | sed -E 's/.*\] MIGRATED +pk=[0-9]+ //' > /tmp/migrated_paths.txt
wc -l /tmp/migrated_paths.txt; head /tmp/migrated_paths.txt     # count = total Migrated; review first
cd "$PRIVATE_MEDIA_ROOT" && xargs -d '\n' -a /tmp/migrated_paths.txt rm -v --
```

Then check that the file counts equal baselines A and B, and that legacy documents still open in the browser.

A full backup of `MEDIA_ROOT` belongs to the later task that deletes its files, not to this runbook.
