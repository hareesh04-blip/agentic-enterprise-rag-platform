"""Step 52 — runtime metadata shape."""

from app.core.runtime_metadata import get_runtime_metadata


def test_runtime_metadata_has_expected_keys() -> None:
    meta = get_runtime_metadata()
    for key in (
        "build_version",
        "process_start_time",
        "process_pid",
        "backend_uptime_seconds",
        "llm_provider",
        "embedding_provider",
        "active_vector_collection",
        "app_env",
        "app_name",
        "stale_process_hint",
    ):
        assert key in meta
    assert isinstance(meta["process_pid"], int)
    assert isinstance(meta["backend_uptime_seconds"], float)
