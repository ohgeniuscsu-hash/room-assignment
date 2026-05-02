import pandas as pd
import pytest
from src.assigner import assign_rooms, validate_combined
from src.occupancy import OccupancyMap


def make_courses(*rows):
    cols = ['과목명', '요일', '교시', '교수명', '학과', '전공',
            '수강제한인원', '온라인여부', '시설요구사항', '합강좌번호', '배정강의실', '잠금']
    return pd.DataFrame(rows, columns=cols)


def make_rooms(*rows):
    cols = ['강의실명', '코드', '층', '수용인원', '특이사항']
    df = pd.DataFrame(rows, columns=cols)
    df['수용인원'] = df['수용인원'].astype(int)
    df['층'] = df['층'].astype(int)
    return df


class TestAssignRooms:
    def test_basic_assignment(self):
        courses = make_courses(
            ('성경신학', '월', '4~6', '김교수', '신학과', '신학석사', '20', '', '', '', '', '')
        )
        rooms = make_rooms(('강의실A', 'A101', 1, 30, ''))
        result, warnings = assign_rooms(courses, rooms, OccupancyMap())
        assert result.loc[0, '배정강의실'] == 'A101'
        assert len(warnings) == 0

    def test_online_course_skipped(self):
        courses = make_courses(
            ('온라인과목', '월', '4~6', '김교수', '신학과', '신학석사', '20', 'Y', '', '', '', '')
        )
        rooms = make_rooms(('강의실A', 'A101', 1, 30, ''))
        result, warnings = assign_rooms(courses, rooms, OccupancyMap())
        assert result.loc[0, '배정강의실'] == '온라인'

    def test_unscheduled_course_flagged(self):
        courses = make_courses(
            ('논문지도', '', '0-0', '김교수', '신학과', '신학석사', '1', '', '', '', '', '')
        )
        rooms = make_rooms(('강의실A', 'A101', 1, 30, ''))
        result, warnings = assign_rooms(courses, rooms, OccupancyMap())
        assert result.loc[0, '배정강의실'] == '시간미배정-검토필요'
        assert len(warnings) == 1

    def test_capacity_exceeded_unassigned(self):
        courses = make_courses(
            ('대형강의', '월', '4~6', '김교수', '신학과', '신학석사', '50', '', '', '', '', '')
        )
        rooms = make_rooms(('강의실A', 'A101', 1, 30, ''))
        result, warnings = assign_rooms(courses, rooms, OccupancyMap())
        assert result.loc[0, '배정강의실'] == '미배정-검토필요'
        assert len(warnings) == 1

    def test_time_conflict_avoided(self):
        occ = OccupancyMap()
        occ.occupy('A101', '월', {4, 5, 6})
        courses = make_courses(
            ('충돌과목', '월', '4~6', '김교수', '신학과', '신학석사', '20', '', '', '', '', '')
        )
        rooms = make_rooms(('강의실A', 'A101', 1, 30, ''))
        result, warnings = assign_rooms(courses, rooms, occ)
        assert result.loc[0, '배정강의실'] == '미배정-검토필요'

    def test_facility_required_hard_constraint(self):
        courses = make_courses(
            ('피아노실기', '월', '4~6', '김교수', '음악과', '음악석사', '5', '', '피아노', '', '', '')
        )
        rooms = make_rooms(
            ('일반강의실', 'A101', 1, 30, ''),
            ('피아노실', 'B201', 2, 10, '피아노'),
        )
        result, warnings = assign_rooms(courses, rooms, OccupancyMap())
        assert result.loc[0, '배정강의실'] == 'B201'

    def test_locked_course_preserved(self):
        courses = make_courses(
            ('성경신학', '월', '4~6', '김교수', '신학과', '신학석사', '20', '', '', '', 'A101', 'Y')
        )
        rooms = make_rooms(
            ('강의실A', 'A101', 1, 30, ''),
            ('강의실B', 'B101', 1, 30, ''),
        )
        result, warnings = assign_rooms(courses, rooms, OccupancyMap())
        assert result.loc[0, '배정강의실'] == 'A101'

    def test_combined_class_same_room(self):
        courses = make_courses(
            ('조직신학(석사)', '월', '4~6', '김교수', '신학과', '신학석사', '10', '', '', 'C001', '', ''),
            ('조직신학(박사)', '월', '4~6', '김교수', '신학과', '신학박사', '5', '', '', 'C001', '', ''),
        )
        rooms = make_rooms(('강의실A', 'A101', 1, 30, ''))
        result, warnings = assign_rooms(courses, rooms, OccupancyMap())
        assert result.loc[0, '배정강의실'] == result.loc[1, '배정강의실']


class TestValidateCombined:
    def test_consistent_combined_passes(self):
        result = make_courses(
            ('조직신학(석사)', '월', '4~6', '김교수', '신학과', '신학석사', '10', '', '', 'C001', 'A101', ''),
            ('조직신학(박사)', '월', '4~6', '김교수', '신학과', '신학박사', '5', '', '', 'C001', 'A101', ''),
        )
        result['배정강의실'] = ['A101', 'A101']
        issues = validate_combined(result)
        assert issues == []

    def test_inconsistent_room_flagged(self):
        result = make_courses(
            ('조직신학(석사)', '월', '4~6', '김교수', '신학과', '신학석사', '10', '', '', 'C001', 'A101', ''),
            ('조직신학(박사)', '월', '4~6', '김교수', '신학과', '신학박사', '5', '', '', 'C001', 'B201', ''),
        )
        result['배정강의실'] = ['A101', 'B201']
        issues = validate_combined(result)
        assert len(issues) == 1
        assert 'C001' in issues[0]['합강좌번호']
