from app.pipeline.materialize_node import shown_build_status


def test_stale_building_without_live_job_is_retryable():
    assert shown_build_status("BUILDING", stale=True, inflight=False) == "FAILED"
    assert shown_build_status("BUILDING", stale=True, inflight=True) == "BUILDING"
    assert shown_build_status("BUILDING", stale=False, inflight=False) == "BUILDING"
    assert shown_build_status("READY", stale=True, inflight=False) == "READY"
    assert shown_build_status(None, stale=True, inflight=False) is None
