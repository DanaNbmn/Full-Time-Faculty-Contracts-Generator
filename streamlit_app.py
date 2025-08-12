# app.py
import streamlit as st
from docx import Document
from io import BytesIO
from datetime import datetime
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

st.set_page_config(page_title="ADU Faculty Contract Generator", page_icon="📄", layout="centered")

# ========= 1) CONFIG =========
DEFAULT_TEMPLATE_PATH = "Faculty_Offer_Letter_Template_Placeholders.docx"
DATE_FORMAT = "%d %B %Y"  # e.g., 11 August 2025

# ========= 2) BENEFITS RULES (from your table) — ONLY the 7 outputs you want =========
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
    joining_value = R["joining_ticket_international"] if is_international else ""

    return {
        "HOUSING_ALLOWANCE": fmt_amt(housing),
        "FURNITURE_ALLOWANCE": fmt_amt(furniture),
        "JOINING_TICKET": joining_value,
        "REPARIATION_ALLOWANCE": fmt_amt(R["repatriation_allowance"]),
        "ANNUAL_LEAVE_DAYS": R["annual_leave_days"],
        "EDUCATION_ALLOWANCE_PER_CHILD": fmt_amt(edu),
        "EDUCATION_ALLOWANCE_TOTAL": fmt_amt(edu),
    }

def replace_placeholders_in_text(text: str, mapping: dict) -> str:
    for k, v in mapping.items():
        token = f"{{{{{k}}}}}"
        if token in text:
            text = text.replace(token, str(v))
    return text

def set_paragraph_text(par, new_text: str):
    for _ in range(len(par.runs)):
        par.runs[0].text = ""
        del par.runs[0]
    par.add_run(new_text)

def insert_paragraph_after(paragraph, text):
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    p = paragraph._parent.add_paragraph()
    p._p = new_p
    set_paragraph_text(p, text)
    return p

def rebuild_benefits_section(doc: Document, mapping: dict):
    """
    Find '3. Benefits' and replace the WHOLE section (until the next '4.' heading)
    with a single, clean block composed from the 7 mapped values.
    This permanently eliminates duplicates from the template.
    """
    # Find start and end
    start_idx = end_idx = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t.startswith("3. Benefits"):
            start_idx = i
        elif start_idx is not None and t.startswith("4."):
            end_idx = i
            break
    if start_idx is None:
        return  # nothing to do

    if end_idx is None:
        end_idx = len(doc.paragraphs)

    # Remove everything AFTER the "3. Benefits" line up to (but not including) end_idx
    for i in range(end_idx - 1, start_idx, -1):
        p = doc.paragraphs[i]
        p._element.getparent().remove(p._element)

    # Compose the clean block
    lines = [
        f"Accommodation: Unfurnished on-campus accommodation based on availability, or a housing allowance of AED {mapping['HOUSING_ALLOWANCE']} per year (paid monthly) will be provided based on eligibility.",
        f"Furniture Allowance: AED {mapping['FURNITURE_ALLOWANCE']} provided at the commencement of employment as a forgivable loan amortized over three (3) years. Should you leave ADU before completing three years of service, the amount will be repayable on a pro-rata basis.",
        "Annual Leave Airfare: Cash in lieu of economy class air tickets for yourself, your spouse, and up to two (2) eligible dependent children under the age of 21 years residing in the UAE, based on ADU’s published schedule of rates including your country of origin. This amount will be paid annually in the month of May, prorated to your joining date.",
    ]
    if mapping.get("JOINING_TICKET"):
        lines.append(f"Commencement Air Tickets: {mapping['JOINING_TICKET']}")
    lines.extend([
        "Repatriation Air Tickets: You will be provided with Economy Class air tickets for yourself, spouse and your eligible dependents (up to 2 children under 21 years) residing in the UAE upon your end of employment to your country of origin.",
        f"Repatriation Allowance: AED {mapping['REPARIATION_ALLOWANCE']} upon conclusion of your contract, applicable only upon completion of two (2) years of continuous service with ADU.",
        "Medical Insurance: You will be provided with medical insurance coverage for yourself, spouse and your eligible dependents (up to 3 children under 21 years) residing in the UAE. (Applicable only for married individuals with spouse/children under their sponsorship)",
        f"Annual Leave Entitlement: {mapping['ANNUAL_LEAVE_DAYS']} calendar days of paid annual leave.",
        f"School Fee Subsidy: An annual subsidy of AED {mapping['EDUCATION_ALLOWANCE_PER_CHILD']} per eligible child under the age of 21 years residing in the UAE under your sponsorship, up to a maximum of AED {mapping['EDUCATION_ALLOWANCE_TOTAL']} per family. This benefit applies only to married individuals with children under their sponsorship.",
        "ADU Tuition Waiver: 75% deduction on tuition fees for self, 50% for dependents and 25% for immediate family in accordance with ADU Policy. (applicable upon completion of one year of service with ADU)",
    ])

    # Insert the new lines right after "3. Benefits"
    anchor = doc.paragraphs[start_idx]
    # Clear any text after replacement (keep the header)
    set_paragraph_text(anchor, "3. Benefits")
    last = anchor
    for line in lines:
        last = insert_paragraph_after(last, line)

def cleanup_global_duplicates(doc: Document):
    """
    If the intro or probation lines appear twice (in separate paragraphs),
    keep the LAST one across the whole document.
    """
    starts = [
        "Abu Dhabi University (ADU) is pleased",
        "Probation Period:",
        "Notice Period:",
    ]
    last_seen = {s: -1 for s in starts}
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        for s in starts:
            if t.startswith(s):
                last_seen[s] = i

    for s, keep_idx in last_seen.items():
        if keep_idx == -1:
            continue
        # delete earlier duplicates
        for i, p in enumerate(list(doc.paragraphs)):
            if i < keep_idx and p.text.strip().startswith(s):
                p._element.getparent().remove(p._element)

def replace_placeholders(doc: Document, mapping: dict):
    # 1) Replace direct placeholders everywhere
    for p in doc.paragraphs:
        set_paragraph_text(p, replace_placeholders_in_text(p.text, mapping))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    set_paragraph_text(p, replace_placeholders_in_text(p.text, mapping))

    # 2) Rebuild Benefits section from scratch (eliminates any template duplicates)
    rebuild_benefits_section(doc, mapping)

    # 3) Remove global duplicates for intro/probation/notice if they exist as separate paras
    cleanup_global_duplicates(doc)

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
        rank = st.selectbox("Rank", [k for k in BENEFITS.keys() if k != "_shared"], index=2)
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

    # DIRECT INPUTS (your exact list)
    base_map = {
        "ID": candidate_id,
        "DATE": today,
        "SALUTATION": salutation,
        "CANDIDATE_NAME": candidate_name,
        "TELEPHONE": telephone,
        "PERSONAL_EMAIL": personal_email,
        "POSITION": position,
        "DEPARTMENT": department,
        "CAMPUS": campus,
        "REPORTING_MANAGER": reporting_manager,
        "SALARY": f"{int(salary):,}" if salary else "",
        "PROBATION": probation,
    }

    # ONLY the 7 benefits fields
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
