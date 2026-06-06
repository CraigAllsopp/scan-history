"""Example: an incremental scan that only reports new findings.

Simulates a scanner that runs repeatedly over a growing corpus. Each run, only
findings that haven't been reported before are surfaced.

Run it twice — the second run reports nothing new unless the corpus changed.
"""
from scan_history import SeenLedger


def scan_corpus():
    """Pretend this inspects files / a DB / the web and returns findings.

    In a real tool the result would change between runs. Here it's fixed so the
    example is deterministic: run #1 reports all three, run #2 reports nothing.
    """
    return [
        {"id": "W001", "msg": "unused import in foo.py"},
        {"id": "W002", "msg": "TODO left in bar.py"},
        {"id": "W003", "msg": "long line in baz.py"},
    ]


def main():
    seen = SeenLedger("scan_seen.json")

    findings = scan_corpus()
    new = seen.new_only(findings, key=lambda f: f["id"])

    if not new:
        print("No new findings since last scan. ")
        return

    print(f"{len(new)} new finding(s):")
    for f in new:
        print(f"  [{f['id']}] {f['msg']}")


if __name__ == "__main__":
    main()
