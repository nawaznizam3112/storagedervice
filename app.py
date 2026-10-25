
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# EU MDR / IVDR TECHNICAL DOCUMENTATION GAP ANALYZER
# Educational and reviewer-support tool; not a conformity verdict.
# ============================================================

APP_VERSION = "1.0.0"

st.set_page_config(
    page_title="EU MDR / IVDR Gap Analyzer",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

STATUSES = ["Draft", "Compliant", "Non-Compliant", "Not Applicable"]

MDR_CLASSES = [
    "Class I",
    "Class Is",
    "Class Im",
    "Class Ir",
    "Class IIa",
    "Class IIb",
    "Class III",
]

IVDR_CLASSES = ["Class A", "Class B", "Class C", "Class D"]


# ------------------------------------------------------------
# Checklist catalogue
# "Default applicability" is a preliminary workflow setting.
# A reviewer must verify actual applicability for each device.
# ------------------------------------------------------------

DOCUMENTATION_ITEMS = [
    {
        "id": "DD-1.1.1",
        "section": "1.1.1",
        "title": "Executive summary",
        "description": "Device overview, regulatory status, key evidence and dossier summary.",
        "criticality": "High",
        "features": [],
    },
    {
        "id": "DD-1.1.2.2",
        "section": "1.1.2.2",
        "title": "Intended purpose and target population",
        "description": "Intended purpose, indications, contraindications, target users and population.",
        "criticality": "Critical",
        "features": [],
    },
    {
        "id": "DD-1.1.2.3",
        "section": "1.1.2.3",
        "title": "Device description and specifications",
        "description": "Principles of operation, configurations, accessories, variants and specifications.",
        "criticality": "Critical",
        "features": [],
    },
    {
        "id": "DD-1.1.2.7",
        "section": "1.1.2.7",
        "title": "UDI hierarchy and identification",
        "description": "UDI-DI/Basic UDI-DI structure and identification records, where applicable.",
        "criticality": "High",
        "features": [],
    },
    {
        "id": "DD-1.2.1",
        "section": "1.2.1",
        "title": "Device classification",
        "description": "Applicable classification rules and rationale.",
        "criticality": "Critical",
        "features": [],
    },
    {
        "id": "DD-1.2.2",
        "section": "1.2.2",
        "title": "Classification justification",
        "description": "Documented rule-by-rule justification for the proposed classification.",
        "criticality": "Critical",
        "features": [],
    },
    {
        "id": "DD-1.3.1",
        "section": "1.3.1",
        "title": "Design history and verification traceability",
        "description": "Design inputs/outputs, verification, validation and traceability records.",
        "criticality": "High",
        "features": [],
    },
    {
        "id": "DD-1.7.3",
        "section": "1.7.3",
        "title": "Verification and validation evidence",
        "description": "Test plans, acceptance criteria, results, deviations and conclusions.",
        "criticality": "High",
        "features": [],
    },
    {
        "id": "DD-1.8.1-4",
        "section": "1.8.1–1.8.4",
        "title": "Software lifecycle and cybersecurity",
        "description": "Software architecture, lifecycle evidence, validation, configuration management and cybersecurity, where relevant.",
        "criticality": "High",
        "features": ["software"],
    },
    {
        "id": "DD-1.9.1-2",
        "section": "1.9.1–1.9.2",
        "title": "Biological safety evaluation",
        "description": "Material characterization, contact categorization and biological evaluation where applicable.",
        "criticality": "High",
        "features": ["patient_contact"],
    },
    {
        "id": "DD-1.10.1",
        "section": "1.10.1",
        "title": "Declaration of Conformity",
        "description": "EU Declaration of Conformity and relevant regulatory particulars.",
        "criticality": "Critical",
        "features": [],
    },
    {
        "id": "DD-1.10.3",
        "section": "1.10.3",
        "title": "SSCP / SSP, where applicable",
        "description": "Summary of Safety and Clinical Performance (MDR) or Summary of Safety and Performance (IVDR), when required.",
        "criticality": "High",
        "features": [],
    },
    {
        "id": "DD-ANNEX-III",
        "section": "Annex III",
        "title": "Post-market surveillance documentation",
        "description": "PMS plan and applicable PMS reports, PSUR and PMPF/PMCF documentation.",
        "criticality": "High",
        "features": [],
    },
    {
        "id": "DD-CLINICAL",
        "section": "Clinical / Performance",
        "title": "Clinical evaluation or performance evaluation",
        "description": "Clinical evaluation and investigation evidence under MDR, or performance evaluation under IVDR.",
        "criticality": "Critical",
        "features": [],
    },
    {
        "id": "DD-RISK",
        "section": "Risk management",
        "title": "Risk management file",
        "description": "Hazard identification, risk estimation/evaluation, controls and residual-risk benefit-risk assessment.",
        "criticality": "Critical",
        "features": [],
    },
    {
        "id": "DD-LABEL",
        "section": "Labelling / IFU",
        "title": "Labels and instructions for use",
        "description": "Labels, IFU, symbols, language requirements and consistency with intended purpose.",
        "criticality": "High",
        "features": [],
    },
    {
        "id": "DD-STERILE",
        "section": "Sterility",
        "title": "Sterilization and sterile barrier evidence",
        "description": "Sterilization validation, packaging validation and maintenance of sterility, where applicable.",
        "criticality": "High",
        "features": ["sterile"],
    },
    {
        "id": "DD-ACTIVE",
        "section": "Active device",
        "title": "Electrical / energy safety and performance",
        "description": "Evidence for relevant active-device hazards, energy delivery and applicable standards.",
        "criticality": "High",
        "features": ["active_energy"],
    },
    {
        "id": "DD-IVDR-CDX",
        "section": "IVDR / Companion diagnostic",
        "title": "Companion diagnostic evidence",
        "description": "Intended-use linkage, performance evidence and relevant consultation requirements, where applicable.",
        "criticality": "High",
        "features": ["companion_diagnostic"],
        "ivdr_only": True,
    },
    {
        "id": "DD-IVDR-SELFTEST",
        "section": "IVDR / Self-test or near-patient",
        "title": "Self-testing / near-patient evidence",
        "description": "Usability, performance and labelling evidence appropriate to the intended user and setting.",
        "criticality": "High",
        "features": ["self_testing"],
        "ivdr_only": True,
    },
]


# GSPR numbers and summaries are indicative descriptions.
# Verify exact legal wording and applicability in the current
# consolidated regulation and applicable guidance/standards.

GSPR_ITEMS = [
    {
        "id": "GSPR-1-9",
        "title": "General safety and performance",
        "mdr": "MDR Annex I, 1–9",
        "ivdr": "IVDR Annex I, 1–9",
        "description": "Safety, performance, risk management and benefit-risk principles.",
        "features": [],
        "criticality": "Critical",
    },
    {
        "id": "GSPR-10",
        "title": "Chemical, physical and biological properties",
        "mdr": "MDR Annex I, 10",
        "ivdr": "IVDR Annex I, 10",
        "description": "Material properties, contamination, residues and biological safety, as relevant.",
        "features": ["patient_contact"],
        "criticality": "High",
    },
    {
        "id": "GSPR-11",
        "title": "Infection and microbial contamination",
        "mdr": "MDR Annex I, 11",
        "ivdr": "IVDR Annex I, 11",
        "description": "Infection risks, microbial contamination and sterile-device requirements, as applicable.",
        "features": ["sterile"],
        "criticality": "High",
    },
    {
        "id": "GSPR-MDR-14",
        "title": "Devices incorporating materials of biological origin",
        "mdr": "MDR Annex I, 13–14 (verify applicable clauses)",
        "ivdr": None,
        "description": "Biological-origin materials and related hazards, if present. This is not a universal software requirement.",
        "features": ["biological_origin"],
        "criticality": "High",
    },
    {
        "id": "GSPR-MDR-17",
        "title": "Programmable electronic systems / software",
        "mdr": "MDR Annex I, 17",
        "ivdr": None,
        "description": "Software and programmable-system requirements, including validation and information security as relevant.",
        "features": ["software"],
        "criticality": "High",
    },
    {
        "id": "GSPR-IVDR-16",
        "title": "Programmable electronic systems / software",
        "mdr": None,
        "ivdr": "IVDR Annex I, 16",
        "description": "Software and programmable-system requirements, including validation and information security as relevant.",
        "features": ["software"],
        "criticality": "High",
    },
    {
        "id": "GSPR-MDR-23",
        "title": "Information supplied by the manufacturer",
        "mdr": "MDR Annex I, 23",
        "ivdr": None,
        "description": "Labels, instructions for use, warnings, symbols and UDI-related information as applicable.",
        "features": [],
        "criticality": "High",
    },
    {
        "id": "GSPR-IVDR-20",
        "title": "Information supplied by the manufacturer",
        "mdr": None,
        "ivdr": "IVDR Annex I, 20",
        "description": "Labels, instructions for use, warnings, symbols and UDI-related information as applicable.",
        "features": [],
        "criticality": "High",
    },
    {
        "id": "GSPR-MDR-14-ACTIVE",
        "title": "Active-device and energy-related safety",
        "mdr": "MDR Annex I, 14 (and other applicable clauses)",
        "ivdr": None,
        "description": "Requirements for active devices and energy-related hazards; verify the precise applicable clauses.",
        "features": ["active_energy"],
        "criticality": "High",
    },
    {
        "id": "GSPR-IVDR-13",
        "title": "Construction and interaction with the environment",
        "mdr": None,
        "ivdr": "IVDR Annex I, 13",
        "description": "Relevant construction, interaction and environmental considerations for the IVD.",
        "features": [],
        "criticality": "Medium",
    },
]


def make_initial_state(items: list[dict[str, Any]]) -> pd.DataFrame:
    """Create the editable review table."""
    return pd.DataFrame(
        [
            {
                "ID": item["id"],
                "Section": item["section"],
                "Requirement / topic": item["title"],
                "Assessment status": "Draft",
                "Reviewer notes": "",
                "Criticality": item["criticality"],
            }
            for item in items
        ]
    )


def feature_enabled(item: dict[str, Any], profile: dict[str, Any]) -> bool:
    """Check whether an item is relevant to selected characteristics."""
    if item.get("ivdr_only") and profile["framework"] != "IVDR":
        return False

    features = item.get("features", [])
    if not features:
        return True

    return all(profile.get(feature, False) for feature in features)


def build_documentation_catalogue(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build the checklist and mark preliminary applicability."""
    result = []

    for item in DOCUMENTATION_ITEMS:
        applicable = feature_enabled(item, profile)
        result.append(
            {
                **item,
                "preliminary_applicability": (
                    "Review required" if applicable else "Potentially not applicable"
                ),
            }
        )

    return result


def build_gspr_catalogue(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Select framework-specific GSPR rows and device-related rows."""
    result = []

    for item in GSPR_ITEMS:
        if profile["framework"] == "MDR":
            reference = item.get("mdr")
        else:
            reference = item.get("ivdr")

        if not reference:
            continue

        if not feature_enabled(item, profile):
            continue

        result.append(
            {
                "ID": item["id"],
                "Requirement / topic": item["title"],
                "Regulatory reference (verify)": reference,
                "Applicability": "Reviewer to confirm",
                "Assessment status": "Draft",
                "Reviewer notes": item["description"],
                "Criticality": item["criticality"],
            }
        )

    return result


def readiness_score(df: pd.DataFrame) -> float:
    """Percentage of reviewed, applicable rows marked compliant.

    Draft and Non-Compliant rows do not count as compliant.
    Not Applicable rows are excluded from the denominator.
    """
    if df.empty:
        return 0.0

    applicable = df[df["Assessment status"] != "Not Applicable"]
    if applicable.empty:
        return 0.0

    compliant = (applicable["Assessment status"] == "Compliant").sum()
    return round(100 * compliant / len(applicable), 1)


def count_completed(df: pd.DataFrame) -> int:
    """Count rows that have a final reviewer disposition."""
    if df.empty:
        return 0
    return int(df["Assessment status"].isin(
        ["Compliant", "Non-Compliant", "Not Applicable"]
    ).sum())


def count_critical_gaps(df: pd.DataFrame) -> int:
    """Count critical rows marked Non-Compliant."""
    if df.empty:
        return 0

    return int(
        (
            (df["Criticality"] == "Critical")
            & (df["Assessment status"] == "Non-Compliant")
        ).sum()
    )


def count_open_gaps(df: pd.DataFrame) -> int:
    """Count non-compliant rows of any criticality."""
    if df.empty:
        return 0
    return int((df["Assessment status"] == "Non-Compliant").sum())


def make_excel_report(
    profile: dict[str, Any],
    documentation_df: pd.DataFrame,
    gspr_df: pd.DataFrame,
) -> bytes:
    """Create a multi-sheet Excel workbook in memory."""
    output = BytesIO()

    profile_rows = [
        {"Field": key, "Value": str(value)}
        for key, value in profile.items()
    ]
    profile_df = pd.DataFrame(profile_rows)

    summary_df = pd.DataFrame(
        [
            {"Metric": "Documentation readiness (%)",
             "Value": readiness_score(documentation_df)},
            {"Metric": "GSPR readiness (%)",
             "Value": readiness_score(gspr_df)},
            {"Metric": "Documentation rows completed",
             "Value": count_completed(documentation_df)},
            {"Metric": "GSPR rows completed",
             "Value": count_completed(gspr_df)},
            {"Metric": "Documentation critical gaps",
             "Value": count_critical_gaps(documentation_df)},
            {"Metric": "GSPR critical gaps",
             "Value": count_critical_gaps(gspr_df)},
            {"Metric": "Documentation non-compliant rows",
             "Value": count_open_gaps(documentation_df)},
            {"Metric": "GSPR non-compliant rows",
             "Value": count_open_gaps(gspr_df)},
        ]
    )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        profile_df.to_excel(writer, sheet_name="Device Profile", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        documentation_df.to_excel(
            writer, sheet_name="Documentation Audit", index=False
        )
        gspr_df.to_excel(writer, sheet_name="GSPR Audit", index=False)

    return output.getvalue()


def make_markdown_report(
    profile: dict[str, Any],
    documentation_df: pd.DataFrame,
    gspr_df: pd.DataFrame,
) -> str:
    """Create a portable audit summary."""
    lines = [
        "# EU MDR / IVDR Gap Analysis Report",
        "",
        f"- Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Application version: {APP_VERSION}",
        "- Report type: preliminary reviewer-support assessment",
        "",
        "## Device profile",
        "",
    ]

    for key, value in profile.items():
        lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Documentation readiness: {readiness_score(documentation_df)}%",
            f"- GSPR readiness: {readiness_score(gspr_df)}%",
            f"- Documentation items with final disposition: "
            f"{count_completed(documentation_df)} / {len(documentation_df)}",
            f"- GSPR items with final disposition: "
            f"{count_completed(gspr_df)} / {len(gspr_df)}",
            f"- Critical documentation gaps: {count_critical_gaps(documentation_df)}",
            f"- Critical GSPR gaps: {count_critical_gaps(gspr_df)}",
            "",
            "## Technical documentation audit",
            "",
            documentation_df.to_markdown(index=False),
            "",
            "## GSPR audit",
            "",
            gspr_df.to_markdown(index=False),
            "",
            "## Limitations",
            "",
            "This report is a preliminary gap-assessment aid, not a conformity "
            "assessment, legal opinion, Notified Body decision, or declaration "
            "that the device meets EU requirements. The checklist is not exhaustive. "
            "Verify legal references, classification, applicability, harmonised "
            "standards, common specifications, transition provisions and current "
            "consolidated legislation against authoritative sources. "
            "All applicability and compliance decisions require documented review.",
            "",
        ]
    )

    return "\n".join(lines)


# ------------------------------------------------------------
# Sidebar: device profile
# ------------------------------------------------------------

st.title("EU MDR / IVDR Technical Documentation & GSPR Gap Analyzer")
st.caption(
    "Structured reviewer workspace for preliminary dossier and Annex I gap assessment"
)

with st.sidebar:
    st.header("Device profile")

    framework_label = st.selectbox(
        "Regulatory framework",
        ["EU MDR 2017/745", "EU IVDR 2017/746"],
    )
    framework = "MDR" if "MDR" in framework_label else "IVDR"

    device_name = st.text_input("Device name", placeholder="e.g. Dental imaging system")
    model = st.text_input("Model / variant", placeholder="Model or catalogue number")
    basic_udi = st.text_input("Basic UDI-DI (if applicable)")
    udi_di = st.text_input("UDI-DI (if assigned)")

    intended_purpose = st.text_area(
        "Stated intended purpose",
        height=130,
        placeholder="Enter the manufacturer's stated intended purpose.",
    )

    intended_user = st.selectbox(
        "Intended user profile",
        ["Healthcare professional", "Lay person", "Both", "Other / mixed"],
    )

    class_options = MDR_CLASSES if framework == "MDR" else IVDR_CLASSES
    assigned_class = st.selectbox("Assigned risk class", class_options)

    st.subheader("Device characteristics")
    software = st.checkbox("Includes software / MDSW")
    patient_contact = st.checkbox("Patient-contacting materials")
    sterile = st.checkbox("Supplied sterile / sterile delivery")
    active_energy = st.checkbox("Administers or delivers active energy")
    companion_diagnostic = st.checkbox(
        "Companion diagnostic",
        disabled=(framework != "IVDR"),
    )
    self_testing = st.checkbox(
        "Self-testing / point-of-care",
        disabled=(framework != "IVDR"),
    )
    biological_origin = st.checkbox(
        "Incorporates materials of biological origin"
    )

    st.divider()
    st.caption("Reviewer details")
    reviewer = st.text_input("Reviewer name / initials")
    organization = st.text_input("Organization")
    assessment_date = st.date_input("Assessment date", value=date.today())


profile = {
    "framework": framework,
    "framework_label": framework_label,
    "device_name": device_name.strip() or "Not entered",
    "model": model.strip() or "Not entered",
    "basic_udi_di": basic_udi.strip() or "Not entered",
    "udi_di": udi_di.strip() or "Not entered",
    "intended_purpose": intended_purpose.strip() or "Not entered",
    "intended_user": intended_user,
    "assigned_class": assigned_class,
    "software": software,
    "patient_contact": patient_contact,
    "sterile": sterile,
    "active_energy": active_energy,
    "companion_diagnostic": companion_diagnostic,
    "self_testing": self_testing,
    "biological_origin": biological_origin,
    "reviewer": reviewer.strip() or "Not entered",
    "organization": organization.strip() or "Not entered",
    "assessment_date": assessment_date.isoformat(),
}

if not device_name.strip():
    st.info(
        "Enter the device name in the sidebar to identify this assessment. "
        "You can still explore the checklist using the default state."
    )

if not intended_purpose.strip():
    st.warning(
        "Intended purpose is blank. Classification, GSPR applicability and "
        "evidence requirements cannot be reliably assessed without it."
    )

if framework == "MDR" and assigned_class in ["Class Is", "Class Im", "Class Ir"]:
    st.info(
        "Confirm that the special Class I designation is justified under the "
        "applicable MDR classification rules and conformity-assessment route."
    )

if framework == "IVDR" and assigned_class == "Class D":
    st.info(
        "Confirm the applicable IVDR Class D classification rule, performance "
        "evidence, and any applicable EU reference laboratory or expert-panel "
        "requirements."
    )


# ------------------------------------------------------------
# Build checklists
# ------------------------------------------------------------

documentation_catalogue = build_documentation_catalogue(profile)
gspr_catalogue = build_gspr_catalogue(profile)

if "documentation_review" not in st.session_state:
    st.session_state.documentation_review = make_initial_state(
        documentation_catalogue
    )

if "gspr_review" not in st.session_state:
    st.session_state.gspr_review = pd.DataFrame(gspr_catalogue)

# Refresh the checklist structure when the regulatory framework or
# device characteristics change, retaining existing review statuses
# and notes for matching row IDs.
doc_defaults = make_initial_state(documentation_catalogue)
old_docs = st.session_state.documentation_review.copy()
if "ID" in old_docs.columns:
    old_docs = old_docs.set_index("ID")
    for idx, row in doc_defaults.iterrows():
        item_id = row["ID"]
        if item_id in old_docs.index:
            for col in ["Assessment status", "Reviewer notes"]:
                if col in old_docs.columns:
                    doc_defaults.at[idx, col] = old_docs.at[item_id, col]
st.session_state.documentation_review = doc_defaults

gspr_defaults = pd.DataFrame(gspr_catalogue)
old_gspr = st.session_state.gspr_review.copy()
if not gspr_defaults.empty and "ID" in old_gspr.columns:
    old_gspr = old_gspr.set_index("ID")
    for idx, row in gspr_defaults.iterrows():
        item_id = row["ID"]
        if item_id in old_gspr.index:
            for col in ["Assessment status", "Reviewer notes", "Applicability"]:
                if col in old_gspr.columns:
                    gspr_defaults.at[idx, col] = old_gspr.at[item_id, col]
st.session_state.gspr_review = gspr_defaults


# ------------------------------------------------------------
# Main tabs
# ------------------------------------------------------------

tab_dashboard, tab_docs, tab_gspr, tab_report = st.tabs(
    ["Dashboard", "Technical documentation", "GSPR mapping", "Export & limitations"]
)

with tab_dashboard:
    st.subheader("Compliance readiness dashboard")

    docs_df = st.session_state.documentation_review
    gspr_df = st.session_state.gspr_review

    docs_score = readiness_score(docs_df)
    gspr_score = readiness_score(gspr_df)
    combined_score = round((docs_score + gspr_score) / 2, 1)

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Documentation readiness", f"{docs_score}%")
    metric2.metric("GSPR readiness", f"{gspr_score}%")
    metric3.metric(
        "Reviewed items",
        f"{count_completed(docs_df) + count_completed(gspr_df)}",
    )
    metric4.metric(
        "Critical gaps",
        f"{count_critical_gaps(docs_df) + count_critical_gaps(gspr_df)}",
    )

    st.progress(combined_score / 100)
    st.caption(
        f"Combined indicative readiness: {combined_score}%. "
        "This is a workflow metric, not a regulatory compliance determination."
    )

    status_frames = []
    for section_name, df in [
        ("Technical documentation", docs_df),
        ("GSPR", gspr_df),
    ]:
        if not df.empty:
            temp = df[["Assessment status"]].copy()
            temp["Audit area"] = section_name
            status_frames.append(temp)

    if status_frames:
        combined = pd.concat(status_frames, ignore_index=True)
        status_counts = (
            combined.groupby(["Audit area", "Assessment status"])
            .size()
            .reset_index(name="Count")
        )

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig = px.bar(
                status_counts,
                x="Assessment status",
                y="Count",
                color="Audit area",
                barmode="group",
                title="Assessment status by audit area",
            )
            st.plotly_chart(fig, use_container_width=True)

        with chart_col2:
            overall_counts = (
                combined["Assessment status"]
                .value_counts()
                .rename_axis("Assessment status")
                .reset_index(name="Count")
            )
            fig = px.pie(
                overall_counts,
                names="Assessment status",
                values="Count",
                title="Overall review disposition",
                hole=0.35,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Items requiring attention")
    open_docs = docs_df[docs_df["Assessment status"] == "Non-Compliant"]
    open_gspr = gspr_df[gspr_df["Assessment status"] == "Non-Compliant"]

    if open_docs.empty and open_gspr.empty:
        st.success(
            "No rows are currently marked Non-Compliant. Draft items still "
            "require review; absence of recorded gaps does not prove compliance."
        )
    else:
        if not open_docs.empty:
            st.write("**Technical documentation gaps**")
            st.dataframe(
                open_docs[
                    ["ID", "Requirement / topic", "Criticality", "Reviewer notes"]
                ],
                use_container_width=True,
                hide_index=True,
            )
        if not open_gspr.empty:
            st.write("**GSPR gaps**")
            st.dataframe(
                open_gspr[
                    ["ID", "Requirement / topic", "Criticality", "Reviewer notes"]
                ],
                use_container_width=True,
                hide_index=True,
            )

with tab_docs:
    st.subheader("Technical documentation checklist")
    st.write(
        "Select a disposition for each row and record objective evidence, "
        "document references, open actions, and rationale in the notes."
    )
    st.caption(
        "The section IDs shown are a configurable starter taxonomy. They are "
        "not a claim that every ID is an official IMDRF nTOC identifier."
    )

    edited_docs = st.data_editor(
        st.session_state.documentation_review,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "ID": st.column_config.TextColumn(disabled=True),
            "Section": st.column_config.TextColumn(disabled=True),
            "Requirement / topic": st.column_config.TextColumn(disabled=True),
            "Criticality": st.column_config.TextColumn(disabled=True),
            "Assessment status": st.column_config.SelectboxColumn(
                options=STATUSES,
                required=True,
            ),
            "Reviewer notes": st.column_config.TextColumn(
                help="Include evidence IDs, rationale, action owner and due date."
            ),
        },
        key="documentation_editor",
    )
    st.session_state.documentation_review = edited_docs

    st.download_button(
        "Download documentation checklist CSV",
        data=edited_docs.to_csv(index=False).encode("utf-8-sig"),
        file_name="technical_documentation_audit.csv",
        mime="text/csv",
    )

with tab_gspr:
    st.subheader("Applicable GSPR review")
    st.write(
        "Rows are selected from the framework and device-characteristic inputs. "
        "The reviewer must confirm applicability against the full Annex I text."
    )

    if st.session_state.gspr_review.empty:
        st.info("No GSPR rows are available for the current profile.")
    else:
        edited_gspr = st.data_editor(
            st.session_state.gspr_review,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "ID": st.column_config.TextColumn(disabled=True),
                "Requirement / topic": st.column_config.TextColumn(disabled=True),
                "Regulatory reference (verify)": st.column_config.TextColumn(
                    disabled=True
                ),
                "Criticality": st.column_config.TextColumn(disabled=True),
                "Applicability": st.column_config.SelectboxColumn(
                    options=[
                        "Reviewer to confirm",
                        "Applicable",
                        "Not Applicable",
                        "Further assessment needed",
                    ],
                    required=True,
                ),
                "Assessment status": st.column_config.SelectboxColumn(
                    options=STATUSES,
                    required=True,
                ),
                "Reviewer notes": st.column_config.TextColumn(
                    help="Record the clause-level rationale and supporting evidence."
                ),
            },
            key="gspr_editor",
        )
        st.session_state.gspr_review = edited_gspr

    st.warning(
        "This is a key-topic mapper, not an exhaustive Annex I checklist. "
        "The software does not automatically infer legal applicability from "
        "the selected checkboxes."
    )

with tab_report:
    st.subheader("Export audit records")

    docs_df = st.session_state.documentation_review
    gspr_df = st.session_state.gspr_review

    excel_bytes = make_excel_report(profile, docs_df, gspr_df)
    markdown_report = make_markdown_report(profile, docs_df, gspr_df)

    st.download_button(
        "Download Excel audit workbook",
        data=excel_bytes,
        file_name="eu_mdr_ivdr_gap_analysis.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        type="primary",
    )

    st.download_button(
        "Download Markdown report",
        data=markdown_report.encode("utf-8"),
        file_name="eu_mdr_ivdr_gap_analysis.md",
        mime="text/markdown",
    )

    st.download_button(
        "Download documentation audit CSV",
        data=docs_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="documentation_audit.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download GSPR audit CSV",
        data=gspr_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="gspr_audit.csv",
        mime="text/csv",
    )

    st.subheader("Assessment profile")
    st.json(profile)

    st.subheader("Regulatory and quality-system limitations")
    st.markdown(
        """
        - This tool does **not** certify conformity or replace a qualified
          regulatory assessment.
        - Verify all references against the current consolidated MDR/IVDR,
          applicable amendments, common specifications, harmonised standards,
          MDCG guidance and relevant national requirements.
        - Classification must be justified under the applicable MDR Annex VIII
          or IVDR Annex VIII rules; the selected class is not independently
          validated by this app.
        - A Basic UDI-DI, UDI-DI, SSCP, SSP, clinical/performance evidence,
          sterilization evidence and other dossier elements are applicable
          according to the device, class, intended purpose and regulatory route.
        - Readiness scores are simple counts of reviewer dispositions. They
          do not weight clinical significance, legal consequences or residual
          risk, and must not be used as evidence of conformity.
        - Before use in a regulated QMS, add controlled document identification,
          versioning, approval/signature controls, access control, backups,
          audit-trail integrity, validation evidence and change management.
        - Do not enter confidential patient information or other sensitive data
          into this demonstration application.
        """
    )

st.divider()
st.caption(
    f"EU MDR / IVDR Gap Analyzer v{APP_VERSION} · "
    "Reviewer-support prototype · Not a conformity assessment"
)
