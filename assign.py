import argparse
from src.config import load_config
from src.loader import load_courses, load_rooms, load_existing_occupancy
from src.occupancy import OccupancyMap
from src.assigner import assign_rooms, validate_combined
from src.exporter import export_result, export_timetable


def main():
    parser = argparse.ArgumentParser(description='대학원 강의실 자동 배정 프로그램')
    parser.add_argument('--courses', required=True, help='대학원 과목 목록 엑셀 파일')
    parser.add_argument('--rooms', required=True, help='강의실 목록 엑셀 파일')
    parser.add_argument('--existing', help='학부 기존 배정 자료 (선택)')
    parser.add_argument('--config', default='config.yaml', help='설정 파일 경로')
    args = parser.parse_args()

    print("설정 파일 로드 중...")
    config = load_config(args.config)

    print("과목 목록 로드 중...")
    courses = load_courses(args.courses, config)

    print("강의실 목록 로드 중...")
    rooms = load_rooms(args.rooms, config)

    print("기존 배정 자료 로드 중...")
    if args.existing:
        base_occ = load_existing_occupancy(args.existing, config)
        print(f"  학부 배정 자료 적용: {args.existing}")
    else:
        base_occ = OccupancyMap()
        print("  학부 배정 자료 없음 (전 시간대 사용 가능)")

    print("강의실 배정 중...")
    result, warnings = assign_rooms(courses, rooms, base_occ)

    print("합강 검증 중...")
    combined_issues = validate_combined(result)

    result_path = config['output']['result']
    timetable_path = config['output']['timetable']

    print(f"결과 저장 중: {result_path}")
    export_result(result, warnings, combined_issues, result_path)

    print(f"시간표 저장 중: {timetable_path}")
    export_timetable(result, rooms, timetable_path)

    print("\n=== 배정 완료 ===")
    total = len(courses)
    assigned = len(result[~result['배정강의실'].str.contains('검토필요', na=False)])
    print(f"전체 과목: {total}개")
    print(f"정상 배정: {assigned}개")
    print(f"검토 필요: {total - assigned}개")

    if warnings:
        print(f"\n⚠️  경고 {len(warnings)}건 → '{result_path}'의 '경고' 시트 확인")
    if combined_issues:
        print(f"⚠️  합강 불일치 {len(combined_issues)}건 → 경고 시트 확인")


if __name__ == '__main__':
    main()
