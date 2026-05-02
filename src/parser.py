import re


def parse_period(period_str: str) -> set[int]:
    """
    "4~6" 또는 "4-6" 형태의 교시 문자열을 교시 번호 집합으로 변환.
    양 끝 포함: "4~6" → {4, 5, 6}
    """
    period_str = str(period_str).strip()
    match = re.search(r'(\d+)\s*[~\-]\s*(\d+)', period_str)
    if not match:
        raise ValueError(f"교시 형식 오류: '{period_str}'")
    start, end = int(match.group(1)), int(match.group(2))
    return set(range(start, end + 1))


def is_unscheduled(period_str) -> bool:
    """
    시간 미배정 과목 감지.
    None, 빈 문자열, '*' 접두사, '0-0' 또는 '0~0' 패턴이면 True.
    """
    if period_str is None:
        return True
    s = str(period_str).strip()
    if not s:
        return True
    if s.startswith('*'):
        return True
    if re.fullmatch(r'0\s*[~\-]\s*0', s):
        return True
    return False
