from pathlib import Path

from app.discovery.snapshot import delete_snapshot, save_snapshot


def test_snapshot_round_trip_and_delete(tmp_path: Path):
    snapshot = save_snapshot("<html><body>test</body></html>", tmp_path)

    assert snapshot.path.exists()
    assert len(snapshot.sha256) == 64
    assert snapshot.observed_at.endswith("+00:00")

    delete_snapshot(snapshot)
    assert not snapshot.path.exists()
