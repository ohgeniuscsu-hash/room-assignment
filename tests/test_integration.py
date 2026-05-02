import subprocess
import sys
from pathlib import Path


def test_full_run_produces_output_files():
    result = subprocess.run(
        [sys.executable, 'assign.py',
         '--courses', 'tests/fixtures/sample_courses.xlsx',
         '--rooms', 'tests/fixtures/sample_rooms.xlsx'],
        capture_output=True, text=True,
        cwd='/Users/ohgenius/room-assignment'
    )
    assert result.returncode == 0, result.stderr
    assert Path('/Users/ohgenius/room-assignment/배정결과.xlsx').exists()
    assert Path('/Users/ohgenius/room-assignment/시간표.xlsx').exists()


def test_piano_course_assigned_to_piano_room():
    import pandas as pd
    result_df = pd.read_excel('/Users/ohgenius/room-assignment/배정결과.xlsx', sheet_name='배정결과')
    piano_row = result_df[result_df['과목명'] == '피아노실기']
    assert len(piano_row) == 1
    assert piano_row.iloc[0]['배정강의실'] == 'M201'


def test_online_course_marked_online():
    import pandas as pd
    result_df = pd.read_excel('/Users/ohgenius/room-assignment/배정결과.xlsx', sheet_name='배정결과')
    online_row = result_df[result_df['과목명'] == '온라인설교학']
    assert online_row.iloc[0]['배정강의실'] == '온라인'


def test_unscheduled_course_flagged():
    import pandas as pd
    result_df = pd.read_excel('/Users/ohgenius/room-assignment/배정결과.xlsx', sheet_name='배정결과')
    thesis_row = result_df[result_df['과목명'] == '논문지도']
    assert thesis_row.iloc[0]['배정강의실'] == '시간미배정-검토필요'


def test_combined_classes_same_room():
    import pandas as pd
    result_df = pd.read_excel('/Users/ohgenius/room-assignment/배정결과.xlsx', sheet_name='배정결과')
    combined = result_df[result_df['합강좌번호'] == 'C001']
    assert len(combined) == 2
    assert combined['배정강의실'].nunique() == 1
