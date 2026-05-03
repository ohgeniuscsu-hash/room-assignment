from unittest.mock import MagicMock, patch
import pandas as pd


SEMESTER = "2025-2학기"
RESULT_DF = pd.DataFrame({"과목명": ["성경신학"], "배정강의실": ["A101"]})
ROOMS_DF = pd.DataFrame({"코드": ["A101"], "수용인원": [30]})


@patch("src.db.get_client")
def test_save_run_starts_at_version_1(mock_get_client):
    from src.db import save_run
    client = MagicMock()
    mock_get_client.return_value = client
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    version = save_run(SEMESTER, RESULT_DF, [], [], ROOMS_DF)

    assert version == 1
    insert_data = client.table.return_value.insert.call_args[0][0]
    assert insert_data["semester"] == SEMESTER
    assert insert_data["version"] == 1


@patch("src.db.get_client")
def test_save_run_increments_version(mock_get_client):
    from src.db import save_run
    client = MagicMock()
    mock_get_client.return_value = client
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{"version": 2}]

    version = save_run(SEMESTER, RESULT_DF, [], [], ROOMS_DF)

    assert version == 3


@patch("src.db.get_client")
def test_list_semesters_deduplicates(mock_get_client):
    from src.db import list_semesters
    client = MagicMock()
    mock_get_client.return_value = client
    client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"semester": "2025-2학기"},
        {"semester": "2025-2학기"},
        {"semester": "2025-1학기"},
    ]

    result = list_semesters()

    assert result == ["2025-2학기", "2025-1학기"]


@patch("src.db.get_client")
def test_list_runs_returns_sorted(mock_get_client):
    from src.db import list_runs
    client = MagicMock()
    mock_get_client.return_value = client
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"id": 1, "version": 1, "created_at": "2025-09-01T10:00:00"},
        {"id": 2, "version": 2, "created_at": "2025-09-02T10:00:00"},
    ]

    result = list_runs(SEMESTER)

    assert len(result) == 2
    assert result[0]["version"] == 1


@patch("src.db.get_client")
def test_get_run_returns_dataframes(mock_get_client):
    from src.db import get_run
    client = MagicMock()
    mock_get_client.return_value = client
    client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "result_json": [{"과목명": "성경신학", "배정강의실": "A101"}],
        "warnings_json": [],
        "combined_issues_json": [],
        "rooms_json": [{"코드": "A101", "수용인원": 30}],
    }

    run = get_run(1)

    assert isinstance(run["result_df"], pd.DataFrame)
    assert run["result_df"].iloc[0]["과목명"] == "성경신학"
    assert run["warnings"] == []
