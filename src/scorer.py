import pandas as pd


def score_room(
    room: pd.Series,
    major: str,
    dept: str,
    enrollment: int,
    assigned_by_major: dict[str, str],
    assigned_rooms_by_dept: dict[str, list[int]],
    has_facility_req: bool,
) -> float:
    score = 0.0
    room_code = str(room['코드'])
    room_floor = int(room['층'])
    room_cap = int(room['수용인원'])

    if assigned_by_major.get(major) == room_code:
        score += 40

    dept_floors = assigned_rooms_by_dept.get(dept, [])
    if dept_floors and room_floor in dept_floors:
        score += 20

    if room_cap > 0:
        score += (1 - (room_cap - enrollment) / room_cap) * 20

    spare = room_cap - enrollment
    if not has_facility_req and not str(room.get('특이사항', '')).strip() and spare >= enrollment // 2:
        score += 20

    return score
