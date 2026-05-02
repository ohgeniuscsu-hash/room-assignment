import pandas as pd
from src.scorer import score_room


def make_room(code, floor, capacity, notes=""):
    return pd.Series({
        '코드': code, '층': floor, '수용인원': capacity, '특이사항': notes, '강의실명': code
    })


class TestScoreRoom:
    def test_same_major_room_scores_40(self):
        room = make_room("101", 1, 30)
        assigned = {"신학석사": "101"}
        score = score_room(room, major="신학석사", dept="신학과",
                           enrollment=20, assigned_by_major=assigned,
                           assigned_rooms_by_dept={"신학과": [1]},
                           has_facility_req=False)
        assert score >= 40

    def test_different_major_same_floor_scores_20(self):
        room = make_room("102", 1, 30)
        assigned = {"다른전공": "103"}
        score = score_room(room, major="신학석사", dept="신학과",
                           enrollment=20, assigned_by_major=assigned,
                           assigned_rooms_by_dept={"신학과": [1]},
                           has_facility_req=False)
        assert score >= 20

    def test_full_room_scores_low_capacity(self):
        room = make_room("101", 1, 21)
        score = score_room(room, major="신학석사", dept="신학과",
                           enrollment=20, assigned_by_major={},
                           assigned_rooms_by_dept={},
                           has_facility_req=False)
        capacity_score = (1 - (21 - 20) / 21) * 20
        assert abs(score - capacity_score) < 1

    def test_no_facility_req_in_plain_room_scores_20(self):
        room = make_room("101", 1, 30, notes="")
        score = score_room(room, major="신학석사", dept="신학과",
                           enrollment=20, assigned_by_major={},
                           assigned_rooms_by_dept={},
                           has_facility_req=False)
        assert score >= 20
