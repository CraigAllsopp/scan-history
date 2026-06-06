"""scan-history — cross-reference before you flag.

A persistent "seen ledger" for scanners, linters, crawlers and any job that
repeatedly looks at the same corpus. The point: report only what's *new*, so a
scan that runs every hour doesn't re-raise the same finding 24 times a day.

The pattern came from building a system that scans a knowledge base for
connections. Without a memory of what it had already surfaced, every run
re-reported everything — noise drowned signal. A scanner that can't remember
what it already said isn't surfacing findings, it's spamming them.

Standalone. Zero dependencies (stdlib json). MIT licensed.

    >>> from scan_history import SeenLedger
    >>> seen = SeenLedger("findings.json")
    >>> seen.new_only(["bug-1", "bug-2"])      # first run
    ['bug-1', 'bug-2']
    >>> seen.new_only(["bug-1", "bug-2", "bug-3"])  # later run
    ['bug-3']
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Callable, Iterable, Sequence

__version__ = "0.1.0"
__all__ = ["SeenLedger"]


class SeenLedger:
    """Tracks which item-keys have already been seen, persistently across runs.

    Keys are arbitrary strings (you choose what identifies a 'finding' —
    a hash, an id, a file:line, a normalised message). The ledger stores each
    key with the timestamp it was first seen.
    """

    def __init__(self, path: str, *, autosave: bool = True):
        self.path = path
        self.autosave = autosave
        self._seen: dict[str, float] = {}
        self._load()

    # ---- persistence ----
    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    self._seen = {str(k): float(v) for k, v in data.items()}
            except (json.JSONDecodeError, ValueError, OSError):
                # corrupt ledger: start fresh rather than crash the scan
                self._seen = {}

    def save(self) -> None:
        """Atomic write — temp file + replace, so a crash mid-write can't corrupt the ledger."""
        d = os.path.dirname(self.path) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".seen_", dir=d)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._seen, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # ---- core API ----
    def is_new(self, key: str) -> bool:
        """True if this key has not been seen before."""
        return str(key) not in self._seen

    def mark(self, key: str, *, when: float | None = None) -> None:
        """Record a key as seen (no-op if already seen — preserves first-seen time)."""
        key = str(key)
        if key not in self._seen:
            self._seen[key] = when if when is not None else time.time()
            if self.autosave:
                self.save()

    def new_only(
        self,
        items: Iterable,
        *,
        key: Callable[[object], str] = str,
        mark: bool = True,
    ) -> list:
        """Return only the items whose key is new; mark them seen by default.

        `key` extracts a stable identity from each item (defaults to str()).
        Set `mark=False` to peek without recording (dry run).
        """
        fresh = []
        new_keys = []
        for item in items:
            k = str(key(item))
            if k not in self._seen and k not in new_keys:
                fresh.append(item)
                new_keys.append(k)
        if mark and new_keys:
            now = time.time()
            for k in new_keys:
                self._seen[k] = now
            if self.autosave:
                self.save()
        return fresh

    def forget(self, key: str) -> bool:
        """Remove a key so it will be treated as new again. Returns True if it was present."""
        key = str(key)
        existed = self._seen.pop(key, None) is not None
        if existed and self.autosave:
            self.save()
        return existed

    def prune(self, *, older_than_seconds: float) -> int:
        """Forget keys first-seen longer ago than the cutoff. Returns count pruned.

        Useful when 'new again after a while' is the desired behaviour
        (e.g. re-surface a finding if it recurs after a quiet period).
        """
        cutoff = time.time() - older_than_seconds
        stale = [k for k, ts in self._seen.items() if ts < cutoff]
        for k in stale:
            del self._seen[k]
        if stale and self.autosave:
            self.save()
        return len(stale)

    def __len__(self) -> int:
        return len(self._seen)

    def __contains__(self, key: object) -> bool:
        return str(key) in self._seen
