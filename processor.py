import pandas as pd
from typing import Union, IO


PIPELINE_STAGES = [
    "1. Link Sent",
    "2. Call Needed (>48h)",
    "3. Slot Confirmed",
    "4. Sent for Jury Approval",
    "5. Approved & Invite Sent",
    "6. Completed",
    "No-Show",
]

TABLE_COLUMNS = [
    "Startup_ID",
    "Startup_Name",
    "Founder_Email",
    "Founder_Phone",
    "Last_Review_Date",
    "Link_Sent",
    "Link_Sent_Date",
    "Assigned_Slot",
    "Pipeline_Stage",
    "Template_Received",
    "Days_Since_Last_Review",
    "Days_Since_Link_Sent",
    "Alert_Flag",
]


def _read_tabular_file(file_source: Union[str, IO]) -> pd.DataFrame:
    """Reads either a CSV or Excel file path / Streamlit UploadedFile object."""
    if isinstance(file_source, str):
        if file_source.lower().endswith(".xlsx"):
            return pd.read_excel(file_source)
        return pd.read_csv(file_source)

    filename = getattr(file_source, "name", "").lower()
    if filename.endswith(".xlsx"):
        return pd.read_excel(file_source)
    return pd.read_csv(file_source)


def load_and_clean(
    master_source: Union[str, IO], slots_source: Union[str, IO]
) -> pd.DataFrame:
    """Loads, cleans, and left-merges the startups master list with QBR review slots."""
    df_master = _read_tabular_file(master_source)
    df_slots = _read_tabular_file(slots_source)

    df_master.columns = [col.strip() for col in df_master.columns]
    df_slots.columns = [col.strip() for col in df_slots.columns]

    df_master["Startup_ID"] = df_master["Startup_ID"].astype(str).str.strip().str.upper()
    df_slots["Startup_ID"] = df_slots["Startup_ID"].astype(str).str.strip().str.upper()

    df = pd.merge(df_master, df_slots, on="Startup_ID", how="left")

    df["Assigned_Slot"] = df["Assigned_Slot"].fillna("").astype(str).str.strip()
    df["Pipeline_Stage"] = df["Pipeline_Stage"].fillna("1. Link Sent").astype(str).str.strip()
    df["Link_Sent_Date"] = df["Link_Sent_Date"].fillna("").astype(str).str.strip()
    df["Link_Sent"] = df["Link_Sent_Date"].ne("")

    df["Template_Received"] = (
        df["Template_Received"]
        .fillna(False)
        .apply(lambda x: str(x).strip().lower() in ["true", "1", "yes", "oui"])
    )

    df = recalculate_metrics(df)
    return df[TABLE_COLUMNS]


def recalculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Recalculates day counters, stage escalations, and action flags after any table edit."""
    df = df.copy()
    today = pd.Timestamp.today().normalize()

    last_rev_dt = pd.to_datetime(df["Last_Review_Date"], errors="coerce")
    df["Last_Review_Date"] = last_rev_dt.dt.strftime("%Y-%m-%d").fillna("")
    df["Days_Since_Last_Review"] = (today - last_rev_dt).dt.days.fillna(0).astype(int)

    link_sent_dt = pd.to_datetime(df["Link_Sent_Date"], errors="coerce")
    df["Days_Since_Link_Sent"] = (today - link_sent_dt).dt.days.fillna(0).astype(int)

    # Auto-escalate if link was sent >= 2 days ago and no slot is assigned
    unbooked_mask = (
        (df["Pipeline_Stage"] == "1. Link Sent")
        & (df["Link_Sent_Date"].astype(str).str.strip().ne(""))
        & (df["Assigned_Slot"].astype(str).str.strip() == "")
        & (df["Days_Since_Link_Sent"] >= 2)
    )
    df.loc[unbooked_mask, "Pipeline_Stage"] = "2. Call Needed (>48h)"

    df["Alert_Flag"] = df.apply(flag_bottlenecks, axis=1)
    return df


def flag_bottlenecks(row: pd.Series) -> str:
    """Assigns a plain-text operational flag based on stage, SLA, and template status."""
    stage = str(row.get("Pipeline_Stage", ""))
    days_review = int(row.get("Days_Since_Last_Review", 0))
    template_ok = bool(row.get("Template_Received", False))
    link_sent_date = str(row.get("Link_Sent_Date", "")).strip()

    if stage == "No-Show":
        return "No-Show (Reschedule)"
    if not link_sent_date and stage == "1. Link Sent":
        return "Send Booking Link"
    if stage == "2. Call Needed (>48h)":
        return "Call to Confirm Slot"
    if stage == "5. Approved & Invite Sent" and not template_ok:
        return "Chase QBR Template"
    if stage == "3. Slot Confirmed":
        return "Ready for Jury Approval"
    if days_review > 90 and stage != "6. Completed":
        return "Overdue (>90d)"

    return "OK"