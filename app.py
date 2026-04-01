import os
import sqlite3
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import streamlit as st

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(
    page_title="TS Group KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#002B6B"   # TS Group blue
ACCENT = "#E0B323"    # TS Group gold
BG = "#F7F9FC"
CARD = "#FFFFFF"
TEXT = "#172033"
MUTED = "#667085"
SUCCESS = "#067647"
WARN = "#B54708"
DANGER = "#B42318"

DB_PATH = os.getenv("KPI_DB_PATH", "kpi_tracker.db")
DEFAULT_LOGO_PATH = os.getenv("TS_LOGO_PATH", "logo2017.png")

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    f"""
    <style>
        .stApp {{
            background: {BG};
            color: {TEXT};
        }}
        .main .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }}
        .ts-header {{
            background: linear-gradient(90deg, {PRIMARY} 0%, #0B3A8F 100%);
            padding: 1.4rem 1.6rem;
            border-radius: 18px;
            color: white;
            margin-bottom: 1.2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        }}
        .ts-subtitle {{
            color: #D0D5DD;
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }}
        .metric-card {{
            background: {CARD};
            border-radius: 18px;
            padding: 1rem 1.1rem;
            border: 1px solid #E6EAF0;
            box-shadow: 0 6px 20px rgba(16, 24, 40, 0.05);
        }}
        .section-card {{
            background: {CARD};
            border-radius: 18px;
            padding: 1rem 1.1rem;
            border: 1px solid #E6EAF0;
            box-shadow: 0 6px 20px rgba(16, 24, 40, 0.05);
            margin-bottom: 1rem;
        }}
        .small-muted {{
            color: {MUTED};
            font-size: 0.88rem;
        }}
        .status-good {{ color: {SUCCESS}; font-weight: 700; }}
        .status-watch {{ color: {WARN}; font-weight: 700; }}
        .status-risk {{ color: {DANGER}; font-weight: 700; }}
        .pill {{
            display: inline-block;
            padding: 0.22rem 0.6rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 0.35rem;
        }}
        .pill-blue {{ background: rgba(0,43,107,0.10); color: {PRIMARY}; }}
        .pill-gold {{ background: rgba(224,179,35,0.16); color: #8A6700; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 999px;
            padding: 0.45rem 0.9rem;
            background: white;
            border: 1px solid #E6EAF0;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Database helpers
# -----------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kpis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pillar TEXT NOT NULL,
            kpi TEXT NOT NULL,
            target TEXT NOT NULL,
            measurement_basis TEXT,
            how_to_measure TEXT,
            how_to_achieve TEXT,
            owner TEXT,
            unit TEXT,
            frequency TEXT DEFAULT 'Monthly',
            baseline_value REAL,
            current_value REAL,
            status TEXT DEFAULT 'Not Started',
            notes TEXT,
            last_updated TEXT,
            connector_key TEXT,
            active INTEGER DEFAULT 1
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kpi_id INTEGER NOT NULL,
            update_date TEXT NOT NULL,
            value_text TEXT,
            progress_note TEXT,
            updated_by TEXT,
            FOREIGN KEY (kpi_id) REFERENCES kpis(id)
        )
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) AS c FROM kpis")
    count = cur.fetchone()["c"]
    if count == 0:
        seed_data(conn)
    conn.close()


def seed_data(conn):
    seed_rows = [
        ("Core IT", "System uptime", "≥ 99%", "Monthly uptime report", "Track availability of critical systems monthly using server, firewall, internet, or monitoring logs. Uptime % = (total available time - downtime) / total time.", "Implement basic monitoring, alerting, preventive maintenance, and prompt recovery for critical systems.", "IT", "%", None, None, "Not Started", "", datetime.now().isoformat(), "monitoring:uptime"),
        ("Core IT", "Critical incident response", "< 2 hrs", "Incident log", "Measure elapsed time between incident report timestamp and first IT response timestamp for critical incidents.", "Define critical incidents clearly, create escalation channel, and ensure on-call acknowledgement discipline.", "IT", "hours", None, None, "Not Started", "", datetime.now().isoformat(), "itsm:critical_response"),
        ("Core IT", "Email migration completion", "100%", "Migration status", "Track migrated users/mailboxes against total approved migration scope.", "Migrate by batches with checklist, testing, and user sign-off.", "IT", "%", None, None, "Not Started", "", datetime.now().isoformat(), "m365:migration"),
        ("Core IT", "No material phishing-related incident resulting in financial loss or prolonged service disruption", "100%", "Cybersecurity incident", "Track whether any material phishing incident causes financial loss or prolonged disruption during the year. Binary pass/fail KPI.", "Strengthen email security, MFA, user awareness, and incident response handling.", "IT / Security", "%", None, None, "Not Started", "", datetime.now().isoformat(), "security:phishing_material"),
        ("Core IT", "Preventive maintenance", "≥ 95%", "Maintenance logs", "Completed planned preventive maintenance tasks divided by total scheduled tasks.", "Maintain monthly maintenance checklist and assign task ownership for sites/systems.", "IT / TST", "%", None, None, "Not Started", "", datetime.now().isoformat(), "ops:pm_completion"),
        ("AI Infrastructure", "AI Core deployment", "Q2", "Deployment milestone", "Check milestone completion: infrastructure provisioned, model deployed, and pilot users able to access.", "Keep scope to pilot architecture first, with one working environment and controlled user access.", "IT / TST", "milestone", None, None, "Not Started", "", datetime.now().isoformat(), "ai:core_deploy"),
        ("AI Infrastructure", "Production AI workflows", "≥ 5", "Live workflow count", "Count workflows that are in live business use, not merely tested or demonstrated.", "Launch the five already-defined workflows first before adding new ones.", "IT / Departments", "count", None, None, "Not Started", "", datetime.now().isoformat(), "ai:workflow_count"),
        ("AI Infrastructure", "Manual hour reduction", "≥ 15%", "Baseline vs pilot", "Compare average process time before and after pilot implementation for selected workflows.", "Choose a few processes with high manual effort and enforce actual usage during pilot.", "IT / Departments", "%", None, None, "Not Started", "", datetime.now().isoformat(), "ai:time_reduction"),
        ("AI Infrastructure", "AI adoption rate", "≥ 40%", "Monthly usage metrics", "Number of active monthly AI users divided by total target users for pilot scope.", "Deploy practical use cases to selected departments and monitor active usage monthly.", "IT / Departments", "%", None, None, "Not Started", "", datetime.now().isoformat(), "ai:monthly_active"),
        ("Operational AI", "Room inspection AI", "≥ 30% drafting reduction", "Baseline vs pilot", "Compare average time taken to prepare room inspection draft reports before and after AI-assisted workflow.", "Use AI to generate first draft while keeping staff as reviewer/final approver.", "Operations / IT", "%", None, None, "Not Started", "", datetime.now().isoformat(), "ops:room_inspection_ai"),
        ("Operational AI", "Self check-in pilot", "≥ 25% time improvement", "Pilot benchmark", "Compare average onboarding time per resident at pilot site before and after kiosk-assisted process.", "Pilot only one site first and streamline form capture, ID capture, and verification steps.", "Operations / IT", "%", None, None, "Not Started", "", datetime.now().isoformat(), "ops:self_checkin"),
        ("Operational AI", "Maintenance data standardisation", "100% pilot sites", "Audit review", "Check whether all pilot sites use the standardised maintenance template and required fields.", "Issue one standard template and enforce usage through site audits and reporting.", "Operations / IT", "%", None, None, "Not Started", "", datetime.now().isoformat(), "ops:maintenance_std"),
        ("TST Financial", "Revenue achievement", "≥ 90% budget", "Financial report", "Compare actual FY2026 revenue against board-approved budget.", "Deliver planned internal chargebacks and approved external projects with timely billing.", "TST", "%", None, None, "Not Started", "", datetime.now().isoformat(), "finance:rev_budget"),
        ("TST Financial", "Net profit", "Positive", "Audited P&L", "Check whether FY2026 audited net profit is above zero.", "Control staffing, project execution cost, and overhead growth while protecting revenue.", "TST", "amount", None, None, "Not Started", "", datetime.now().isoformat(), "finance:net_profit"),
        ("TST Financial", "Cost control", "±5% variance", "Budget vs actual", "Compare total actual costs against approved FY2026 budget and calculate variance percentage.", "Review actual spend monthly and escalate variances early before year-end.", "TST", "%", None, None, "Not Started", "", datetime.now().isoformat(), "finance:cost_variance"),
        ("TST Financial", "Recurring revenue", "≥ 50%", "Revenue analysis", "Recurring platform/support revenue divided by total revenue.", "Maintain recurring internal support lines and progressively add managed service revenue.", "TST", "%", None, None, "Not Started", "", datetime.now().isoformat(), "finance:recurring_mix"),
    ]

    conn.executemany(
        """
        INSERT INTO kpis (
            pillar, kpi, target, measurement_basis, how_to_measure, how_to_achieve,
            owner, unit, baseline_value, current_value, status, notes, last_updated, connector_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        seed_rows,
    )
    conn.commit()


# -----------------------------
# Data access
# -----------------------------
def load_kpis() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM kpis WHERE active = 1 ORDER BY pillar, id", conn)
    conn.close()
    return df


def load_updates(kpi_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM updates WHERE kpi_id = ? ORDER BY update_date DESC, id DESC",
        conn,
        params=(kpi_id,),
    )
    conn.close()
    return df


def save_kpi_update(kpi_id: int, current_value, status: str, notes: str, updated_by: str):
    conn = get_conn()
    cur = conn.cursor()
    ts = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        "UPDATE kpis SET current_value = ?, status = ?, notes = ?, last_updated = ? WHERE id = ?",
        (current_value, status, notes, ts, kpi_id),
    )
    cur.execute(
        "INSERT INTO updates (kpi_id, update_date, value_text, progress_note, updated_by) VALUES (?, ?, ?, ?, ?)",
        (kpi_id, ts, str(current_value), notes, updated_by),
    )
    conn.commit()
    conn.close()


def update_kpi_metadata(kpi_id: int, owner: str, baseline, frequency: str, target: str, measurement_basis: str, how_to_measure: str, how_to_achieve: str):
    conn = get_conn()
    cur = conn.cursor()
    ts = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        """
        UPDATE kpis
        SET owner = ?, baseline_value = ?, frequency = ?, target = ?, measurement_basis = ?,
            how_to_measure = ?, how_to_achieve = ?, last_updated = ?
        WHERE id = ?
        """,
        (owner, baseline, frequency, target, measurement_basis, how_to_measure, how_to_achieve, ts, kpi_id),
    )
    conn.commit()
    conn.close()


# -----------------------------
# Connector placeholders
# -----------------------------
def connector_registry() -> dict:
    return {
        "monitoring:uptime": "Future connector: uptime monitor / Prometheus / Uptime Kuma / cloud monitor",
        "itsm:critical_response": "Future connector: ticketing system / incident form / email inbox parser",
        "m365:migration": "Future connector: Microsoft Graph / migration tracker",
        "security:phishing_material": "Future connector: Defender / SIEM / security incident register",
        "ops:pm_completion": "Future connector: maintenance system / Google Sheet / internal app",
        "ai:core_deploy": "Future connector: deployment job / server heartbeat",
        "ai:workflow_count": "Future connector: internal workflow registry / API",
        "ai:time_reduction": "Future connector: workflow logs / timesheet / process tracker",
        "ai:monthly_active": "Future connector: auth logs / API usage store",
        "ops:room_inspection_ai": "Future connector: inspection app database",
        "ops:self_checkin": "Future connector: kiosk logs / e-Dorm onboarding stats",
        "ops:maintenance_std": "Future connector: maintenance audit sheet",
        "finance:rev_budget": "Future connector: accounting system / Xero export",
        "finance:net_profit": "Future connector: P&L import",
        "finance:cost_variance": "Future connector: budget vs actual spreadsheet",
        "finance:recurring_mix": "Future connector: accounting classification rules",
    }


def seeded_connector_status(df: pd.DataFrame) -> pd.DataFrame:
    registry = connector_registry()
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "KPI": r["kpi"],
                "Connector Key": r["connector_key"],
                "Future Integration Path": registry.get(r["connector_key"], "Custom API / CSV / database adapter"),
            }
        )
    return pd.DataFrame(rows)


# -----------------------------
# Utility functions
# -----------------------------
def status_class(status: str) -> str:
    status = (status or "").lower()
    if status in {"on track", "complete", "achieved"}:
        return "status-good"
    if status in {"watch", "in progress", "partially achieved"}:
        return "status-watch"
    return "status-risk"


def parse_target_percent(target: str):
    if not isinstance(target, str):
        return None
    digits = "".join(ch for ch in target if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def summarize(df: pd.DataFrame):
    total = len(df)
    on_track = int(df["status"].isin(["On Track", "Complete", "Achieved"]).sum())
    watch = int(df["status"].isin(["Watch", "In Progress", "Partially Achieved"]).sum())
    risk = total - on_track - watch
    return total, on_track, watch, risk


# -----------------------------
# Initialize
# -----------------------------
init_db()
df = load_kpis()


# -----------------------------
# Header
# -----------------------------
left, right = st.columns([0.7, 0.3])
with left:
    st.markdown(
        f"""
        <div class='ts-header'>
            <div style='display:flex;align-items:center;gap:16px;'>
                <div>
                    <div style='font-size:1.7rem;font-weight:800;'>TS Group KPI Dashboard</div>
                    <div class='ts-subtitle'>FY2026 Innovation & Technology Workplan tracker with manual updates today and connector-ready architecture for future automation.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with right:
    if Path(DEFAULT_LOGO_PATH).exists():
        st.image(DEFAULT_LOGO_PATH, use_column_width=True)
    else:
        st.markdown(
            f"<div class='section-card'><b>Logo not found.</b><br><span class='small-muted'>Set TS_LOGO_PATH or place logo2017.png beside the app.</span></div>",
            unsafe_allow_html=True,
        )

# Summary cards
summary_total, summary_on_track, summary_watch, summary_risk = summarize(df)
cols = st.columns(4)
metrics = [
    ("Active KPIs", summary_total, "Total tracked commitments"),
    ("On Track / Complete", summary_on_track, "Healthy progress"),
    ("Watch", summary_watch, "Needs follow-up"),
    ("At Risk / Not Started", summary_risk, "Needs action"),
]
for c, (title, value, subtitle) in zip(cols, metrics):
    with c:
        st.markdown(
            f"<div class='metric-card'><div class='small-muted'>{title}</div><div style='font-size:2rem;font-weight:800;color:{PRIMARY};'>{value}</div><div class='small-muted'>{subtitle}</div></div>",
            unsafe_allow_html=True,
        )

# Sidebar filters
with st.sidebar:
    st.markdown("## Filters")
    pillar_filter = st.multiselect("Pillar", sorted(df["pillar"].unique()), default=sorted(df["pillar"].unique()))
    status_filter = st.multiselect("Status", sorted(df["status"].fillna("Not Started").unique()), default=sorted(df["status"].fillna("Not Started").unique()))
    owner_filter = st.multiselect("Owner", sorted(df["owner"].fillna("Unassigned").unique()), default=sorted(df["owner"].fillna("Unassigned").unique()))
    search = st.text_input("Search KPI", placeholder="Search by KPI or notes...")
    st.markdown("---")
    st.markdown("### Future integrations")
    st.caption("The app is structured to let you later plug in Microsoft 365, Xero exports, CSV uploads, API logs, or internal systems without changing the KPI model.")

filtered = df[df["pillar"].isin(pillar_filter) & df["status"].isin(status_filter) & df["owner"].isin(owner_filter)]
if search:
    mask = filtered["kpi"].str.contains(search, case=False, na=False) | filtered["notes"].str.contains(search, case=False, na=False)
    filtered = filtered[mask]

# Tabs
summary_tab, update_tab, detail_tab, connector_tab = st.tabs(["Executive Summary", "Update KPI", "KPI Detail", "Future Connectors"])

with summary_tab:
    st.markdown("### KPI Portfolio")
    display_df = filtered[[
        "pillar", "kpi", "target", "measurement_basis", "owner", "frequency", "current_value", "status", "last_updated"
    ]].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("### By Pillar")
    pillar_summary = (
        filtered.groupby("pillar")
        .agg(total_kpis=("id", "count"), on_track=("status", lambda s: int(s.isin(["On Track", "Complete", "Achieved"]).sum())))
        .reset_index()
    )
    if not pillar_summary.empty:
        pillar_summary["progress_ratio"] = (pillar_summary["on_track"] / pillar_summary["total_kpis"] * 100).round(1)
        st.dataframe(pillar_summary, use_container_width=True, hide_index=True)

with update_tab:
    st.markdown("### Manual KPI Update")
    kpi_options = {f"{row['pillar']} — {row['kpi']}": int(row["id"]) for _, row in filtered.iterrows()}
    if not kpi_options:
        st.info("No KPI available with current filters.")
    else:
        selected_label = st.selectbox("Select KPI", list(kpi_options.keys()))
        selected_id = kpi_options[selected_label]
        row = df[df["id"] == selected_id].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            current_value = st.text_input("Current Value", value="" if pd.isna(row["current_value"]) else str(row["current_value"]))
            status = st.selectbox("Status", ["Not Started", "In Progress", "On Track", "Watch", "At Risk", "Complete", "Achieved"], index=["Not Started", "In Progress", "On Track", "Watch", "At Risk", "Complete", "Achieved"].index(row["status"]) if row["status"] in ["Not Started", "In Progress", "On Track", "Watch", "At Risk", "Complete", "Achieved"] else 0)
            updated_by = st.text_input("Updated By", value="HIT")
        with col2:
            notes = st.text_area("Progress Note", value=row["notes"] or "", height=140)

        if st.button("Save KPI Update", type="primary"):
            save_kpi_update(selected_id, current_value, status, notes, updated_by)
            st.success("KPI updated successfully.")
            st.rerun()

        st.markdown("### Edit KPI Definition")
        with st.expander("Open KPI metadata editor"):
            owner = st.text_input("Owner", value=row["owner"] or "")
            baseline = st.text_input("Baseline Value", value="" if pd.isna(row["baseline_value"]) else str(row["baseline_value"]))
            frequency = st.selectbox("Frequency", ["Monthly", "Quarterly", "One-off", "Annual"], index=["Monthly", "Quarterly", "One-off", "Annual"].index(row["frequency"]) if row["frequency"] in ["Monthly", "Quarterly", "One-off", "Annual"] else 0)
            target = st.text_input("Target", value=row["target"] or "")
            measurement_basis = st.text_input("Measurement Basis", value=row["measurement_basis"] or "")
            how_to_measure = st.text_area("How to Measure", value=row["how_to_measure"] or "", height=120)
            how_to_achieve = st.text_area("How to Achieve", value=row["how_to_achieve"] or "", height=120)
            if st.button("Save KPI Definition"):
                baseline_val = None if baseline.strip() == "" else float(baseline)
                update_kpi_metadata(selected_id, owner, baseline_val, frequency, target, measurement_basis, how_to_measure, how_to_achieve)
                st.success("KPI definition updated.")
                st.rerun()

with detail_tab:
    st.markdown("### KPI Detail View")
    detail_options = {f"{row['pillar']} — {row['kpi']}": int(row["id"]) for _, row in filtered.iterrows()}
    if not detail_options:
        st.info("No KPI available with current filters.")
    else:
        selected_label = st.selectbox("Select KPI for detail", list(detail_options.keys()), key="detail_select")
        selected_id = detail_options[selected_label]
        row = df[df["id"] == selected_id].iloc[0]

        st.markdown(
            f"""
            <div class='section-card'>
                <span class='pill pill-blue'>{row['pillar']}</span>
                <span class='pill pill-gold'>{row['frequency']}</span>
                <div style='font-size:1.25rem;font-weight:800;margin-top:0.6rem'>{row['kpi']}</div>
                <div class='small-muted' style='margin-top:0.4rem'>Owner: {row['owner'] or 'Unassigned'} &nbsp;&nbsp;|&nbsp;&nbsp; Target: {row['target']} &nbsp;&nbsp;|&nbsp;&nbsp; Status: <span class='{status_class(row['status'])}'>{row['status']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Measurement Basis")
            st.write(row["measurement_basis"] or "-")
            st.markdown("#### How to Measure")
            st.write(row["how_to_measure"] or "-")
        with c2:
            st.markdown("#### How to Achieve")
            st.write(row["how_to_achieve"] or "-")
            st.markdown("#### Notes")
            st.write(row["notes"] or "-")

        updates_df = load_updates(selected_id)
        st.markdown("#### Update History")
        if updates_df.empty:
            st.caption("No updates yet.")
        else:
            st.dataframe(updates_df[["update_date", "value_text", "progress_note", "updated_by"]], use_container_width=True, hide_index=True)

with connector_tab:
    st.markdown("### Connector Readiness")
    st.caption("These are placeholder mappings to make future automation easier. Today you can update manually; later you can connect APIs, exports, or databases.")
    conn_df = seeded_connector_status(filtered)
    st.dataframe(conn_df, use_container_width=True, hide_index=True)

    st.markdown("### Suggested future integration path")
    st.markdown(
        """
        1. **CSV / Excel import layer** for budget, maintenance, and manual operational data.  
        2. **Microsoft 365 / Graph API** for migration status and possibly usage logs.  
        3. **Xero export/API adapter** for revenue, cost, and recurring revenue calculations.  
        4. **Internal workflow databases** for AI usage, room inspection, and kiosk timing.  
        5. **Security / monitoring feeds** for uptime and incident indicators.  
        """
    )

st.markdown("---")
st.caption("Built for TS Group — designed for immediate manual use and future connector-based automation.")
