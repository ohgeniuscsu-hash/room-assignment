import io
import base64
from pathlib import Path

import streamlit as st

from src.config import load_config
from src.loader import load_courses, load_rooms, load_existing_occupancy
from src.assigner import assign_rooms, validate_combined
from src.exporter import export_result, export_timetable
from src.occupancy import OccupancyMap
from src.db import save_run, list_semesters, list_runs, get_run


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

tab1, tab2 = st.tabs(["📋 배정", "🗂 이력"])

with tab1:
    st.markdown("### ① 파일 업로드")

    semester = st.text_input("학기", placeholder="예: 2025-2학기")

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

    ready = bool(semester.strip()) and courses_file is not None and rooms_file is not None

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
        st.caption("학기명, 과목 목록, 강의실 목록을 모두 입력/업로드해야 실행 버튼이 활성화됩니다.")

    if run_clicked:
        with st.spinner("배정 중..."):
            courses_df = load_courses(courses_file, config)
            rooms_df   = load_rooms(rooms_file, config)
            base_occ   = OccupancyMap()
            if existing_file is not None:
                base_occ = load_existing_occupancy(existing_file, config)
            result_df, warnings = assign_rooms(courses_df, rooms_df, base_occ)
            combined_issues     = validate_combined(result_df)

        try:
            version = save_run(semester.strip(), result_df, warnings, combined_issues, rooms_df)
            st.session_state["saved_version"]  = version
            st.session_state["saved_semester"] = semester.strip()
            st.session_state.pop("save_error", None)
        except Exception as e:
            st.session_state["save_error"] = str(e)

        st.session_state["result_df"]       = result_df
        st.session_state["warnings"]        = warnings
        st.session_state["combined_issues"] = combined_issues
        st.session_state["rooms_df"]        = rooms_df
        st.rerun()

    if "result_df" in st.session_state:
        result_df       = st.session_state["result_df"]
        warnings        = st.session_state["warnings"]
        combined_issues = st.session_state["combined_issues"]
        rooms_df        = st.session_state["rooms_df"]

        st.markdown("### ② 배정 결과")

        if "saved_version" in st.session_state:
            st.caption(f"💾 {st.session_state['saved_semester']} v{st.session_state['saved_version']} 저장됨")
        if "save_error" in st.session_state:
            st.error(f"DB 저장 실패 (배정 결과는 아래에서 다운로드 가능): {st.session_state['save_error']}")

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

        st.markdown("---")
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

with tab2:
    st.markdown("### 🗂 배정 이력")

    try:
        semesters = list_semesters()
    except Exception as e:
        st.error(f"DB 연결 실패: {e}")
        semesters = []

    if not semesters:
        st.info("저장된 이력이 없습니다.")
    else:
        selected_semester = st.selectbox("학기 선택", semesters)
        runs = list_runs(selected_semester)
        run_options = {
            f"v{r['version']} ({r['created_at'][:16].replace('T', ' ')})": r["id"]
            for r in runs
        }

        # ── 단일 버전 조회 ────────────────────────────────────────
        st.markdown("#### 단일 버전 조회")
        single_label = st.selectbox("버전 선택", list(run_options.keys()), key="single_run")

        if st.button("조회", key="btn_view"):
            st.session_state["hist_run"]   = get_run(run_options[single_label])
            st.session_state["hist_label"] = single_label

        if "hist_run" in st.session_state:
            run_data    = st.session_state["hist_run"]
            h_result_df = run_data["result_df"]
            h_warnings  = run_data["warnings"]
            h_combined  = run_data["combined_issues"]
            h_rooms_df  = run_data["rooms_df"]

            st.markdown(f"**{st.session_state['hist_label']}** 결과")

            display_cols = ["과목명", "전공", "요일", "교시", "수강제한인원", "배정강의실"]
            show_cols    = [c for c in display_cols if c in h_result_df.columns]
            st.dataframe(h_result_df[show_cols], use_container_width=True, hide_index=True)

            XLSX_MIME       = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            h_result_buf    = io.BytesIO()
            h_timetable_buf = io.BytesIO()
            export_result(h_result_df, h_warnings, h_combined, h_result_buf)
            export_timetable(h_result_df, h_rooms_df, h_timetable_buf)
            h_result_buf.seek(0)
            h_timetable_buf.seek(0)
            hdl1, hdl2, *_ = st.columns([2, 2, 3])
            with hdl1:
                st.download_button(
                    "📥 배정결과.xlsx", data=h_result_buf,
                    file_name="배정결과.xlsx", mime=XLSX_MIME,
                    use_container_width=True, key="hist_dl1",
                )
            with hdl2:
                st.download_button(
                    "📅 시간표.xlsx", data=h_timetable_buf,
                    file_name="시간표.xlsx", mime=XLSX_MIME,
                    use_container_width=True, key="hist_dl2",
                )

        # ── 버전 비교 ────────────────────────────────────────────
        if len(runs) >= 2:
            st.markdown("---")
            st.markdown("#### 버전 비교")
            cmp_col1, cmp_col2 = st.columns(2)
            with cmp_col1:
                v1_label = st.selectbox("이전 버전", list(run_options.keys()), key="cmp_v1")
            with cmp_col2:
                v2_label = st.selectbox(
                    "이후 버전", list(run_options.keys()),
                    index=min(1, len(run_options) - 1), key="cmp_v2",
                )

            if st.button("비교", key="btn_cmp"):
                st.session_state["cmp_run1"]   = get_run(run_options[v1_label])
                st.session_state["cmp_run2"]   = get_run(run_options[v2_label])
                st.session_state["cmp_labels"] = (v1_label, v2_label)

            if "cmp_run1" in st.session_state:
                df1 = st.session_state["cmp_run1"]["result_df"]
                df2 = st.session_state["cmp_run2"]["result_df"]
                l1, l2 = st.session_state["cmp_labels"]

                merged = df1[["과목명", "배정강의실"]].merge(
                    df2[["과목명", "배정강의실"]],
                    on="과목명",
                    suffixes=(f"_{l1}", f"_{l2}"),
                )
                changed = merged[
                    merged[f"배정강의실_{l1}"] != merged[f"배정강의실_{l2}"]
                ].reset_index(drop=True)

                if changed.empty:
                    st.success("두 버전 간 차이 없음")
                else:
                    st.warning(f"변경된 과목 **{len(changed)}**건")
                    st.markdown("**변경 목록**")
                    for _, row in changed.iterrows():
                        st.write(
                            f"• **{row['과목명']}** — "
                            f"{row[f'배정강의실_{l1}']} → {row[f'배정강의실_{l2}']}"
                        )

                    st.markdown("**나란히 비교**")
                    changed_names = set(changed["과목명"])

                    def _cmp_row_style(row):
                        if row["과목명"] in changed_names:
                            return ["background-color:#FFF8EC"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        merged.style.apply(_cmp_row_style, axis=1),
                        use_container_width=True,
                        hide_index=True,
                    )
