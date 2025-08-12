# app.py
import streamlit as st
from docx import Document
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="ADU Faculty Contract Generator", page_icon="📄", layout="centered")

# ========= 1) CONFIG =========
DEFAULT_TEMPLATE_PATH = "Faculty_Offer_Letter_Template_Placeholders.docx"
DATE_FORMAT = "%d %B %Y"  # e.g., 11 August 2025

# ========= 2) BENEFITS RULES (from your table) =========
BENEFITS = {
    "_shared": {
        "children_school_allowance": {"AD/Dubai": 60000, "AA": 50000},
    },
    "Professor": {
        "annual_leave_days": 56,
        "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
        "repatriation_allowance": 3000,
    },
    "Associate / Sr. Lecturer": {
        "annual_leave_days": 56,
        "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
        "repatriation_allowance": 3000,
    },
    "Assistant / Lecturer": {
        "annual_leave_days": 56,
        "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
        "repatriation_allowance": 3000,
    },
    "Senior Instructor": {
        "annual_leave_days": 42,
        "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 35, "Married": 45}, "AA": {"Single": 30, "Married": 40}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 12, "Married": 15}, "AA": {"Single": 12, "Married": 15}},
        "repatriation_allowance": 2000,
    },
    "Instructor": {
        "annual_leave_days": 42,
        "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 35, "Married": 45}, "AA": {"Single": 30, "Married": 40}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 12, "Married": 15}, "AA": {"Single": 12, "Married": 15}},
        "repatriation_allowance": 2000,
    },
}

# ========= 3) HELPERS =========
def campus_key(campus: str) -> str:
    # Dubai follows Abu Dhabi rules
    return "AD/Dubai" if campus in ["Abu Dhabi", "Dubai", "AD/Dubai"] else "AA"

def fmt_amt(n: int) -> str:
    return f"{int(n):,}"

def compute_benefits_mapping(rank: str, marital: str, campus: str, is_international: bool):
    R = BENEFITS[rank]
    S = BENEFITS["_shared"]
    ckey = campus_key(campus)

    housing = R["housing_allowance_k"][ckey][marital] * 1000
    furniture = R["furniture_allowance_k_once"][ckey][marital] * 1000
    edu = S["children_school_allowance"][ckey]

    # Commencement (joining) ticket only for international hires
    joining_value = R["joining_ticket_international"] if is_international else ""

    # ONLY the 7 placeholders you requested:
    return {
        "HOUSING_ALLOWANCE": fmt_amt(housing),
        "FURNITURE_ALLOWANCE": fmt_amt(furniture),
        "JOINING_TICKET": joining_value,
        "REPARIATION_ALLOWANCE": fmt_amt(R["repatriation_allowance"]),
        "ANNUAL_LEAVE_DAYS": R["annual_leave_days"],
        "EDUCATION_ALLOWANCE_PER_CHILD": fmt_amt(edu),
        "EDUCATION_ALLOWANCE_TOTAL": fmt_amt(edu),
    }

def replace_placeholders(doc: Document, mapping: dict):
    """
    1) Replace placeholders in all paragraphs/cells.
    2) If JOINING_TICKET is empty, remove the 'Commencement Air Tickets:' paragraph.
    3) De-duplicate paragraphs that contain the same clause twice (keep the last).
    """
    # Phrases to guard against duplication within ONE paragraph
    DEDUP_STARTS = [
        "Abu Dhabi University (ADU) is pleased",
        "Probation Period:",
        "Accommodation:",
        "Furniture Allowance:",
        "Annual Leave Airfare:",
        "Commencement Air Tickets:",
        "Relocation Allowance:",
        "Repatriation Air Tickets:",
        "Repatriation Allowance:",
        "Medical Insurance:",
        "Annual Leave Entitlement:",
        "School Fee Subsidy:",
        "ADU Tuition Waiver:",
    ]

    def dedup_line(text: str) -> str:
        for start in DEDUP_STARTS:
            first = text.find(start)
            if first != -1:
                last = text.rfind(start)
                if last != first:
                    # keep only from the last occurrence onward
                    text = text[last:]
        return text

    def replace_and_clean(par):
        text = par.text

        # 1) Replace placeholders
        for k, v in mapping.items():
            token = f"{{{{{k}}}}}"
            if token in text:
                text = text.replace(token, str(v))

        # 2) Remove entire line if it's the Commencement line and JOINING_TICKET is blank
        if mapping.get("JOINING_TICKET", "") == "" and text.strip().startswith("Commencement Air Tickets:"):
            text = ""

        # 3) De-duplicate doubled content inside the same paragraph
        text = dedup_line(text)

        # Rebuild runs cleanly
        for _ in range(len(par.runs)):
            par.runs[0].text = ""
            del par.runs[0]
        par.add_run(text)

    # Apply to all paragraphs
    for p in doc.paragraphs:
        replace_and_clean(p)

    # Apply to all table cells too (if any exist)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_and_clean(p)

def generate_docx(template_bytes: bytes | None, mapping: dict) -> bytes:
    doc = Document(BytesIO(template_bytes)) if template_bytes else Document(DEFAULT_TEMPLATE_PATH)
    replace_placeholders(doc, mapping)
    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out.getvalue()

# ========= 4) UI =========
st.title("📄 ADU – Faculty Offer Letter Generator")

with st.form("offer_form", clear_on_submit=False):
    st.subheader("Candidate & Position")
    c1, c2 = st.columns(2)
    with c1:
        candidate_id = st.text_input("ID (Ref)", placeholder="TEG/2025/001")
        salutation = st.selectbox("Salutation", ["Dr.", "Mr.", "Ms.", "Prof.", "Eng."], index=0)
        candidate_name = st.text_input("Candidate Name", placeholder="Full Name")
        telephone = st.text_input("Telephone", placeholder="+971-XX-XXX-XXXX")
        personal_email = st.text_input("Personal Email", placeholder="name@example.com")
    with c2:
        position = st.text_input("Position", placeholder="Assistant Professor in ...")
        department = st.text_input("Department", placeholder="College/Department")
        reporting_manager = st.text_input("Reporting Manager’s Title", placeholder="Dean/Chair of ...")
        campus = st.selectbox("Campus", ["Abu Dhabi", "Dubai", "Al Ain"], index=0)
        salary = st.number_input("Total Monthly Compensation (AED)", min_value=0, step=500, value=0)

    st.subheader("Contract Settings")
    c3, c4, c5, c6 = st.columns(4)
    with c3:
        rank = st.selectbox("Rank", [k for k in BENEFITS.keys() if k != "_shared"], index=2)  # default Assistant / Lecturer
    with c4:
        marital_status = st.selectbox("Marital Status", ["Single", "Married"], index=0)
    with c5:
        hire_type = st.selectbox("Hire Type", ["Local", "International"], index=0)
    with c6:
        probation = st.number_input("Probation (months)", min_value=1, max_value=12, value=6, step=1)

    st.divider()
    uploaded_template = st.file_uploader("Upload custom DOCX template (optional). Otherwise uses default.", type=["docx"])

    submit = st.form_submit_button("Generate Offer Letter")

if submit:
    today = datetime.now().strftime(DATE_FORMAT)

    # DIRECT INPUTS (exact placeholders you listed)
    base_map = {
        "ID": candidate_id,
        "DATE": today,
        "SALUTATION": salutation,
        "CANDIDATE_NAME": candidate_name,
        "TELEPHONE": telephone,
        "PERSONAL_EMAIL": personal_email,
        "POSITION": position,
        "DEPARTMENT": department,
        "CAMPUS": campus,  # single source of truth
        "REPORTING_MANAGER": reporting_manager,
        "SALARY": f"{int(salary):,}" if salary else "",
        "PROBATION": probation,
    }

    # ONLY the 7 benefits placeholders
    benefits_map = compute_benefits_mapping(
        rank=rank,
        marital=marital_status,
        campus=campus,
        is_international=(hire_type == "International"),
    )

    mapping = {**base_map, **benefits_map}

    try:
        tpl_bytes = uploaded_template.read() if uploaded_template else None
        docx_bytes = generate_docx(tpl_bytes, mapping)
        st.success("Offer letter generated successfully.")
        st.download_button(
            "⬇️ Download Offer Letter (DOCX)",
            data=docx_bytes,
            file_name=f"Offer_{(candidate_name or 'Candidate').replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        st.info(f"Rank: {rank} | Marital: {marital_status} | Campus: {campus} | Hire: {hire_type}")
    except Exception as e:
        st.error(f"Generation failed: {e}")
