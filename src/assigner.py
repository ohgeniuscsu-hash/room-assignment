import pandas as pd
from src.occupancy import OccupancyMap
from src.parser import parse_period, is_unscheduled
from src.scorer import score_room


def assign_rooms(
    courses: pd.DataFrame,
    rooms: pd.DataFrame,
    base_occupancy: OccupancyMap,
) -> tuple[pd.DataFrame, list[dict]]:
    result = courses.copy()
    if '배정강의실' not in result.columns:
        result['배정강의실'] = ''
    if '잠금' not in result.columns:
        result['잠금'] = ''

    occ = base_occupancy
    warnings = []

    combined_enrollment: dict[str, int] = {}
    for combo_id, group in courses[courses['합강좌번호'].str.strip() != ''].groupby('합강좌번호'):
        total = pd.to_numeric(group['수강제한인원'], errors='coerce').fillna(0).sum()
        combined_enrollment[str(combo_id)] = int(total)

    for idx, row in courses.iterrows():
        if str(row.get('잠금', '')).strip().upper() == 'Y':
            assigned = str(row.get('배정강의실', '')).strip()
            day = str(row.get('요일', '')).strip()
            period_str = str(row.get('교시', '')).strip()
            if assigned and day and not is_unscheduled(period_str):
                try:
                    periods = parse_period(period_str)
                    occ.occupy(assigned, day, periods)
                except ValueError:
                    pass
            result.at[idx, '배정강의실'] = assigned

    non_locked = result[result['잠금'].str.strip().str.upper() != 'Y'].copy()
    major_order = (
        non_locked.groupby('전공').size().sort_values(ascending=False).index.tolist()
    )

    assigned_by_major: dict[str, str] = {}
    assigned_rooms_by_dept: dict[str, list[int]] = {}
    combined_assigned: dict[str, str] = {}

    for major in major_order:
        group_df = non_locked[non_locked['전공'] == major].sort_values('교시')
        for idx, row in group_df.iterrows():
            name = str(row['과목명'])
            day = str(row['요일']).strip()
            period_str = str(row['교시']).strip()
            online = str(row.get('온라인여부', '')).strip()
            facility_req = str(row.get('시설요구사항', '')).strip()
            combo_id = str(row.get('합강좌번호', '')).strip()
            dept = str(row['학과'])

            if online:
                result.at[idx, '배정강의실'] = '온라인'
                continue

            if is_unscheduled(period_str) or not day:
                result.at[idx, '배정강의실'] = '시간미배정-검토필요'
                warnings.append({'과목명': name, '사유': '시간 미배정 (검토 필요)'})
                continue

            try:
                periods = parse_period(period_str)
            except ValueError:
                result.at[idx, '배정강의실'] = '시간미배정-검토필요'
                warnings.append({'과목명': name, '사유': f'교시 형식 오류: {period_str}'})
                continue

            enrollment = int(pd.to_numeric(row.get('수강제한인원', 0), errors='coerce') or 0)

            if combo_id and combo_id in combined_assigned:
                room_code = combined_assigned[combo_id]
                result.at[idx, '배정강의실'] = room_code
                occ.occupy(room_code, day, periods)
                continue

            effective_enrollment = combined_enrollment.get(combo_id, enrollment) if combo_id else enrollment

            candidates = []
            for _, room in rooms.iterrows():
                room_code = str(room['코드'])
                room_cap = int(room['수용인원'])
                room_notes = str(room.get('특이사항', '')).strip()

                if effective_enrollment > room_cap:
                    continue
                if facility_req and facility_req not in room_notes:
                    continue
                if not occ.is_available(room_code, day, periods):
                    continue

                candidates.append(room)

            if not candidates:
                result.at[idx, '배정강의실'] = '미배정-검토필요'
                warnings.append({'과목명': name, '사유': '배정 가능한 강의실 없음'})
                continue

            best_room = max(
                candidates,
                key=lambda r: (
                    score_room(r, major, dept, effective_enrollment,
                               assigned_by_major, assigned_rooms_by_dept,
                               has_facility_req=bool(facility_req)),
                    -int(r['수용인원'])
                )
            )

            room_code = str(best_room['코드'])
            result.at[idx, '배정강의실'] = room_code
            occ.occupy(room_code, day, periods)
            assigned_by_major[major] = room_code
            floor = int(best_room['층'])
            assigned_rooms_by_dept.setdefault(dept, [])
            if floor not in assigned_rooms_by_dept[dept]:
                assigned_rooms_by_dept[dept].append(floor)

            if combo_id:
                combined_assigned[combo_id] = room_code

    return result, warnings


def validate_combined(result: pd.DataFrame) -> list[dict]:
    issues = []
    combined_groups = result[result['합강좌번호'].str.strip() != '']
    for combo_id, group in combined_groups.groupby('합강좌번호'):
        rooms_assigned = group['배정강의실'].unique()
        days = group['요일'].unique()
        periods = group['교시'].unique()
        if len(rooms_assigned) > 1 or len(days) > 1 or len(periods) > 1:
            issues.append({
                '합강좌번호': str(combo_id),
                '과목목록': group['과목명'].tolist(),
                '배정강의실목록': rooms_assigned.tolist(),
                '사유': '합강 과목 간 요일/교시/강의실 불일치'
            })
    return issues
