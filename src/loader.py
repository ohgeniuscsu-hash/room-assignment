import re
import pandas as pd
from src.config import col
from src.occupancy import OccupancyMap
from src.parser import parse_period, is_unscheduled


def load_courses(path: str, config: dict) -> pd.DataFrame:
    c = config['courses']
    df = pd.read_excel(path, dtype=str).fillna('')
    rename_map = {v: k for k, v in c.items() if v in df.columns}
    df = df.rename(columns=rename_map)
    for key in c.keys():
        if key not in df.columns:
            df[key] = ''
    return df


def load_rooms(path: str, config: dict) -> pd.DataFrame:
    c = config['rooms']
    df = pd.read_excel(path, dtype=str).fillna('')
    rename_map = {v: k for k, v in c.items() if v in df.columns}
    df = df.rename(columns=rename_map)
    df['수용인원'] = pd.to_numeric(df['수용인원'], errors='coerce').fillna(0).astype(int)
    df['층'] = pd.to_numeric(df['층'], errors='coerce').fillna(0).astype(int)
    return df


def load_existing_occupancy(path: str, config: dict) -> OccupancyMap:
    occ = OccupancyMap()
    df = pd.read_excel(path, dtype=str).fillna('')
    cols = df.columns.tolist()

    if any('요일' in c for c in cols):
        _parse_type_a(df, occ, config)
    else:
        _parse_type_b(df, occ)
    return occ


def _parse_type_a(df: pd.DataFrame, occ: OccupancyMap, config: dict) -> None:
    c = config['courses']
    rename_map = {v: k for k, v in c.items() if v in df.columns}
    df = df.rename(columns=rename_map)
    room_col = config['rooms']['코드'] if config['rooms']['코드'] in df.columns else '강의실코드'

    for _, row in df.iterrows():
        day = str(row.get('요일', '')).strip()
        period_str = str(row.get('교시', '')).strip()
        room_code = str(row.get(room_col, '')).strip()
        if not day or not room_code or is_unscheduled(period_str):
            continue
        try:
            periods = parse_period(period_str)
            occ.occupy(room_code, day, periods)
        except ValueError:
            pass


def _parse_type_b(df: pd.DataFrame, occ: OccupancyMap) -> None:
    room_col = df.columns[0]
    for _, row in df.iterrows():
        room_code = str(row[room_col]).strip()
        if not room_code:
            continue
        for col_name in df.columns[1:]:
            cell = str(row[col_name]).strip()
            if cell.upper() not in ('O', 'Y', '1', 'V', '√', 'TRUE', '○'):
                continue
            match = re.match(r'([가-힣]+)(\d+)', str(col_name))
            if match:
                day, period = match.group(1), int(match.group(2))
                occ.occupy(room_code, day, {period})
