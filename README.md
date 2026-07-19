# scan-history

[![tests](https://github.com/CraigAllsopp/scan-history/actions/workflows/tests.yml/badge.svg)](https://github.com/CraigAllsopp/scan-history/actions/workflows/tests.yml)

**A persistent "seen ledger" for anything that scans the same thing repeatedly.** Report only what's *new*.

Zero dependencies · MIT licensed · Python 3.10+

## Why

A scanner that runs on a schedule has a problem: every run, it finds the same things. A linter re-reports the same warnings. A crawler re-surfaces the same pages. A connection-finder re-raises the same connections. Run it hourly and you get the same noise 24 times a day — and the one genuinely new finding drowns in the repeats.

The fix is a memory of what you've already reported:

```python
from scan_history import SeenLedger

seen = SeenLedger("findings.json")

# first run — everything is new
seen.new_only(["bug-1", "bug-2"])            # -> ['bug-1', 'bug-2']

# an hour later, one new finding — only that one comes back
seen.new_only(["bug-1", "bug-2", "bug-3"])   # -> ['bug-3']
```

That's the whole idea: **cross-reference before you flag.** A scanner that can't remember what it already said isn't surfacing findings, it's spamming them.

This came out of building a system that scans a knowledge base for connections. The first version re-reported everything every cycle. Adding a seen-ledger turned a wall of noise into a short list of genuinely-new items — which is the only list worth a human's attention.

## Install

```bash
pip install scan-history     # (when published)
# or, for now:
pip install -e .
```

## Use

```python
from scan_history import SeenLedger

seen = SeenLedger("seen.json")          # persists here; loads on construct

# the common case — filter a batch down to new items, recording them:
new_items = seen.new_only(my_findings)

# choose what counts as "the same finding" with a key function:
new_bugs = seen.new_only(bugs, key=lambda b: b["fingerprint"])

# peek without recording (dry run):
would_report = seen.new_only(my_findings, mark=False)

# single-item checks:
if seen.is_new("finding-x"):
    alert("finding-x")
    seen.mark("finding-x")

# re-surface things after a quiet period (e.g. weekly digest):
seen.prune(older_than_seconds=7 * 24 * 3600)

# force one item to be treated as new again:
seen.forget("finding-x")
```

## API

- `SeenLedger(path, *, autosave=True)` — load/create a ledger at `path`
- `.new_only(items, *, key=str, mark=True) -> list` — return only items whose key is unseen (and mark them, unless `mark=False`)
- `.is_new(key) -> bool`
- `.mark(key, *, when=None)` — record a key as seen (preserves first-seen time if already present)
- `.forget(key) -> bool` — treat it as new again
- `.prune(*, older_than_seconds) -> int` — forget entries older than a cutoff; returns count removed
- `len(ledger)` / `key in ledger`

## Design notes

- **Atomic writes.** The ledger saves via temp-file-then-`os.replace`, so a crash mid-write can never leave you with a half-written (corrupt) ledger.
- **Corrupt-tolerant.** If the ledger file is somehow unreadable, it starts fresh rather than crashing the scan that depends on it. A dedup helper should never be the thing that takes down your scanner.
- **You choose identity.** The `key` function decides what "the same finding" means — a hash, an id, a normalised message, a `file:line`. Two findings with the same key are the same finding.

## Tests

```bash
pip install pytest && pytest
```

## Licence

MIT — see [LICENSE](LICENSE).

---

*One of a set of small tools extracted from systems I build as independent R&D. More at [my profile](https://github.com/CraigAllsopp).*
