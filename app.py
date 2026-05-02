import io
import base64
from pathlib import Path

import streamlit as st

from src.config import load_config
from src.loader import load_courses, load_rooms, load_existing_occupancy
from src.assigner import assign_rooms, validate_combined
from src.exporter import export_result, export_timetable
from src.occupancy import OccupancyMap


def _logo_b64() -> str:
    p = Path(__file__).parent / "csu_seal.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


st.set_page_config(
    page_title="강의실 배정 시스템",
    page_icon="🎓",
    layout="wide",
)

logo = _logo_b64()
logo_tag = (
    f'<img src="data:image/png;base64,{logo}" '
    f'style="height:48px;border-radius:50%;flex-shrink:0;">'
    if logo else ""
)
st.markdown(f"""
<style>
  .block-container {{ padding-top: 0 !important; }}
</style>
<div style="background:#1A2C5E;padding:14px 40px;display:flex;
            align-items:center;gap:16px;margin-bottom:28px;">
  {logo_tag}
  <span style="color:#FFFFFF;font-size:20px;font-weight:700;letter-spacing:-0.3px;">
    총신대학교 대학원&nbsp;&nbsp;강의실 배정 시스템
  </span>
</div>
""", unsafe_allow_html=True)

config = load_config()

# ── ① 파일 업로드 ──────────────────────────────────────────────
st.markdown("### ① 파일 업로드")
col1, col2, col3 = st.columns(3)

with col1:
    courses_file = st.file_uploader(
        "과목 목록", type=["xlsx"],
        help="필수 — 강좌번호, 과목명, 전공, 요일, 교시, 수강제한인원 등"
    )

with col2:
    rooms_file = st.file_uploader(
        "강의실 목록", type=["xlsx"],
        help="필수 — 코드, 강의실명, 수용인원, 층, 특이사항"
    )

with col3:
    existing_file = st.file_uploader(
        "기존 점유 현황", type=["xlsx"],
        help="선택 — 학부 등 이미 배정된 시간표. 없으면 업로드 생략"
    )

ready = courses_file is not None and rooms_file is not None

st.markdown("")
run_col, _ = st.columns([1, 4])
with run_col:
    run_clicked = st.button(
        "▶  배정 실행",
        disabled=not ready,
        type="primary",
        use_container_width=True,
    )

if not ready:
    st.caption("과목 목록과 강의실 목록 파일을 모두 올려야 실행 버튼이 활성화됩니다.")

if run_clicked:
    with st.spinner("배정 중..."):
        courses_df = load_courses(courses_file, config)
        rooms_df   = load_rooms(rooms_file, config)

        base_occ = OccupancyMap()
        if existing_file is not None:
            base_occ = load_existing_occupancy(existing_file, config)

        result_df, warnings     = assign_rooms(courses_df, rooms_df, base_occ)
        combined_issues         = validate_combined(result_df)

    st.session_state["result_df"]       = result_df
    st.session_state["warnings"]        = warnings
    st.session_state["combined_issues"] = combined_issues
    st.session_state["rooms_df"]        = rooms_df
    st.rerun()

# ── ② 배정 결과 ────────────────────────────────────────────────
if "result_df" in st.session_state:
    result_df       = st.session_state["result_df"]
    warnings        = st.session_state["warnings"]
    combined_issues = st.session_state["combined_issues"]

    st.markdown("### ② 배정 결과")

    total      = len(result_df)
    n_issues   = result_df["배정강의실"].str.contains("검토필요", na=False).sum()
    n_warnings = len(warnings) + len(combined_issues)

    if n_issues or n_warnings:
        st.warning(
            f"배정 완료 · 총 **{total}**개 과목 — "
            f"미배정/검토필요 **{n_issues}**건, 경고 **{n_warnings}**건"
        )
    else:
        st.success(f"배정 완료 · 총 **{total}**개 과목 — 이상 없음 ✓")

    display_cols = ["과목명", "전공", "요일", "교시", "수강제한인원", "배정강의실"]
    show_cols    = [c for c in display_cols if c in result_df.columns]
    view_df      = result_df[show_cols].copy()

    def _row_style(row):
        v = str(row.get("배정강의실", ""))
        if "검토필요" in v:
            return ["background-color:#FFF8EC"] * len(row)
        return [""] * len(row)

    def _cell_style(v):
        return "color:#4A7DC1;font-weight:600" if v == "온라인" else ""

    styled = (
        view_df.style
        .apply(_row_style, axis=1)
        .map(_cell_style, subset=["배정강의실"])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    all_warnings = warnings + combined_issues
    if all_warnings:
        with st.expander(f"⚠ 경고 {len(all_warnings)}건 보기"):
            for w in all_warnings:
                name = w.get("과목명") or w.get("합강좌번호", "")
                st.write(f"• **{name}** — {w.get('사유', '')}")

    # ── 다운로드 ────────────────────────────────────────────────
    st.markdown("---")
    rooms_df = st.session_state["rooms_df"]

    result_buf    = io.BytesIO()
    timetable_buf = io.BytesIO()

    export_result(result_df, warnings, combined_issues, result_buf)
    export_timetable(result_df, rooms_df, timetable_buf)

    result_buf.seek(0)
    timetable_buf.seek(0)

    XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    dl1, dl2, *_ = st.columns([2, 2, 3])
    with dl1:
        st.download_button(
            "📥 배정결과.xlsx",
            data=result_buf,
            file_name="배정결과.xlsx",
            mime=XLSX_MIME,
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            "📅 시간표.xlsx",
            data=timetable_buf,
            file_name="시간표.xlsx",
            mime=XLSX_MIME,
            use_container_width=True,
        )
