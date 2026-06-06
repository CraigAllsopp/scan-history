"""Tests for scan-history."""
import os
from scan_history import SeenLedger


def test_new_only_first_run_returns_all(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    assert led.new_only(["a", "b"]) == ["a", "b"]


def test_new_only_second_run_returns_only_new(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    led.new_only(["a", "b"])
    assert led.new_only(["a", "b", "c"]) == ["c"]


def test_persistence_across_instances(tmp_path):
    p = str(tmp_path / "s.json")
    SeenLedger(p).new_only(["x"])
    # new instance loads the saved ledger
    led2 = SeenLedger(p)
    assert led2.new_only(["x", "y"]) == ["y"]


def test_is_new_and_mark(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    assert led.is_new("k") is True
    led.mark("k")
    assert led.is_new("k") is False
    assert "k" in led


def test_dry_run_does_not_mark(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    led.new_only(["a"], mark=False)
    assert led.is_new("a") is True


def test_key_function(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    items = [{"id": 1, "msg": "x"}, {"id": 2, "msg": "y"}]
    fresh = led.new_only(items, key=lambda d: d["id"])
    assert len(fresh) == 2
    # same ids, different msg -> still seen
    again = led.new_only([{"id": 1, "msg": "changed"}], key=lambda d: d["id"])
    assert again == []


def test_dedupes_within_single_call(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    assert led.new_only(["a", "a", "b"]) == ["a", "b"]


def test_forget(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    led.mark("k")
    assert led.forget("k") is True
    assert led.is_new("k") is True
    assert led.forget("nope") is False


def test_prune_old_entries(tmp_path):
    led = SeenLedger(str(tmp_path / "s.json"))
    led.mark("old", when=0.0)         # epoch — very old
    led.mark("recent")
    pruned = led.prune(older_than_seconds=60)
    assert pruned == 1
    assert led.is_new("old") is True
    assert led.is_new("recent") is False


def test_corrupt_ledger_starts_fresh(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{ not valid json")
    led = SeenLedger(str(p))          # must not raise
    assert len(led) == 0
    assert led.new_only(["a"]) == ["a"]


def test_atomic_save_leaves_no_temp(tmp_path):
    p = str(tmp_path / "s.json")
    led = SeenLedger(p)
    led.new_only(["a", "b", "c"])
    leftovers = [f for f in os.listdir(tmp_path) if f.startswith(".seen_")]
    assert leftovers == []
