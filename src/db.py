import pandas as pd
import streamlit as st
from supabase import create_client, Client


def get_client() -> Client:
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["key"])


def save_run(
    semester: str,
    result_df: pd.DataFrame,
    warnings: list[dict],
    combined_issues: list[dict],
    rooms_df: pd.DataFrame,
    *,
    client: Client = None,
) -> int:
    if client is None:
        client = get_client()
    res = (
        client.table("assignment_runs")
        .select("version")
        .eq("semester", semester)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    version = (res.data[0]["version"] + 1) if res.data else 1
    client.table("assignment_runs").insert({
        "semester": semester,
        "version": version,
        "result_json": result_df.to_dict(orient="records"),
        "warnings_json": warnings,
        "combined_issues_json": combined_issues,
        "rooms_json": rooms_df.to_dict(orient="records"),
    }).execute()
    return version


def list_semesters(*, client: Client = None) -> list[str]:
    if client is None:
        client = get_client()
    res = (
        client.table("assignment_runs")
        .select("semester")
        .order("created_at", desc=True)
        .execute()
    )
    seen: list[str] = []
    for row in res.data:
        if row["semester"] not in seen:
            seen.append(row["semester"])
    return seen


def list_runs(semester: str, *, client: Client = None) -> list[dict]:
    if client is None:
        client = get_client()
    res = (
        client.table("assignment_runs")
        .select("id,version,created_at")
        .eq("semester", semester)
        .order("version")
        .execute()
    )
    return res.data


def get_run(run_id: int, *, client: Client = None) -> dict:
    if client is None:
        client = get_client()
    res = (
        client.table("assignment_runs")
        .select("*")
        .eq("id", run_id)
        .single()
        .execute()
    )
    row = res.data
    return {
        "result_df": pd.DataFrame(row["result_json"]),
        "warnings": row["warnings_json"],
        "combined_issues": row["combined_issues_json"],
        "rooms_df": pd.DataFrame(row["rooms_json"]),
    }
