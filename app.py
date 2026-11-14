import streamlit as st
import pandas as pd
from datetime import datetime
import processor
import templates

st.set_page_config(
    page_title="Prototype 1",
    layout="wide"
)

st.title("Prototype 1")

with st.sidebar:
    st.header("Data Source")
    master_file = st.file_uploader("Upload Startups Master (CSV/XLSX)", type=["csv", "xlsx"])
    slots_file = st.file_uploader("Upload Review Slots (CSV/XLSX)", type=["csv", "xlsx"])
    use_demo = st.toggle("Load Anonymized Demo Data", value=True)
    if st.button("Reset Table State"):
        st.session_state.pop("qbr_table_df", None)
        st.session_state.pop("data_source_sig", None)
        st.rerun()

source_sig = (
    getattr(master_file, "name", None),
    getattr(slots_file, "name", None),
    use_demo,
)

if st.session_state.get("data_source_sig") != source_sig:
    st.session_state["data_source_sig"] = source_sig
    if master_file and slots_file:
        st.session_state["qbr_table_df"] = processor.load_and_clean(master_file, slots_file)
    elif use_demo:
        st.session_state["qbr_table_df"] = processor.load_and_clean(
            "sample_data/startups_master.csv",
            "sample_data/review_slots.csv",
        )
    else:
        st.session_state["qbr_table_df"] = None

df = st.session_state.get("qbr_table_df")

if df is not None:
    tab1, tab2 = st.tabs(["Operational Table", "Automated Message Templates"])

    with tab1:
        st.subheader("QBR Operational Table")
        st.caption("Check 'Link Sent' to automatically stamp today's date into 'Link Sent Date'.")

        edited_df = st.data_editor(
            df,
            key="qbr_editor",
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            column_order=[
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
            ],
            column_config={
                "Startup_ID": st.column_config.TextColumn("ID", disabled=True),
                "Startup_Name": st.column_config.TextColumn("Startup", disabled=True),
                "Founder_Email": st.column_config.TextColumn("Email", disabled=True),
                "Founder_Phone": st.column_config.TextColumn("Phone", disabled=True),
                "Last_Review_Date": st.column_config.TextColumn("Last Review Date"),
                "Link_Sent": st.column_config.CheckboxColumn("Link Sent"),
                "Link_Sent_Date": st.column_config.TextColumn("Link Sent Date"),
                "Assigned_Slot": st.column_config.TextColumn("Assigned Slot"),
                "Pipeline_Stage": st.column_config.SelectboxColumn(
                    "Stage",
                    options=processor.PIPELINE_STAGES,
                    required=True,
                ),
                "Template_Received": st.column_config.CheckboxColumn("Template"),
                "Days_Since_Last_Review": st.column_config.NumberColumn(
                    "Days Since Last Review", disabled=True
                ),
                "Days_Since_Link_Sent": st.column_config.NumberColumn(
                    "Days Since Link Sent", disabled=True
                ),
                "Alert_Flag": st.column_config.TextColumn("Action Flag", disabled=True),
            },
        )

        today_str = datetime.today().strftime("%Y-%m-%d")
        updated_df = edited_df.copy()

        for idx in updated_df.index:
            prev_checked = bool(df.loc[idx, "Link_Sent"])
            curr_checked = bool(updated_df.loc[idx, "Link_Sent"])
            curr_date = str(updated_df.loc[idx, "Link_Sent_Date"]).strip()

            if curr_checked and not prev_checked:
                updated_df.loc[idx, "Link_Sent_Date"] = today_str
            elif not curr_checked and prev_checked:
                updated_df.loc[idx, "Link_Sent_Date"] = ""
            elif curr_date != "" and not curr_checked:
                updated_df.loc[idx, "Link_Sent"] = True

        updated_df = processor.recalculate_metrics(updated_df)

        if not updated_df.equals(df):
            st.session_state["qbr_table_df"] = updated_df
            st.rerun()

        st.download_button(
            "Export Updated Tracker (CSV)",
            data=updated_df.to_csv(index=False).encode("utf-8"),
            file_name=f"qbr_operational_tracker_{today_str.replace('-', '')}.csv",
            mime="text/csv",
        )

    with tab2:
        st.subheader("Automated Message Templates Hub")
        st.markdown("Select a template subject, pick a startup, enter your name, and copy the auto-generated email.")

        template_choice = st.selectbox(
            "Template Subject",
            list(templates.TEMPLATES.keys())
        )

        st.markdown("---")

        col_inp1, col_inp2 = st.columns(2)

        with col_inp1:
            startup_names_list = df["Startup_Name"].tolist()
            selected_startup_name = st.selectbox("Select Startup", startup_names_list)

        with col_inp2:
            user_name_input = st.text_input("Your Name (Sender)", value="Safia")

        startup_row = df[df["Startup_Name"] == selected_startup_name].iloc[0]

        rendered_message = templates.render_template(
            template_choice, startup_row, user_name_input
        )

        st.markdown("##### Generated Email Preview")
        st.code(rendered_message, language=None)
        st.caption("Use the copy icon on the top right of the code block above to copy the message instantly.")

else:
    st.info("Upload your master and slot files in the sidebar or enable Load Anonymized Demo Data.")