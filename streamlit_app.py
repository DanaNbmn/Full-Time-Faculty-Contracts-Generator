import re
import streamlit as st
from docx import Document
from io import BytesIO
from datetime import datetime
from docx.oxml import OxmlElement

st.set_page_config(page_title="ADU Faculty Contract Generator", page_icon="📄", layout="centered")

DEFAULT_TEMPLATE_PATH = "Faculty_Offer_Letter_Template_Placeholders.docx"
DATE_FORMAT = "%d %B %Y"

BENEFITS = {
    "_shared": {"children_school_allowance": {"AD/Dubai": 60000, "AA": 50000}},
    "Professor": {"annual_leave_days": 56, "joining_ticket_international": "1+1+2 Economy",
                  "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
                  "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
                  "repatriation_allowance": 3000},
    "Associate / Sr. Lecturer": {"annual_leave_days": 56, "joining_ticket_international": "1+1+2 Economy",
                  "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
                  "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
                  "repatriation_allowance": 3000},
    "Assistant / Lecturer": {"annual_leave_days": 56, "joining_ticket_international": "1+1+2 Economy",
                  "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
                  "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
                  "repatriation_allowance": 3000},
    "Senior Instructor": {"annual_leave_days": 42, "joining_ticket_international": "1+1+2 Economy",
                  "housing_allowance_k": {"AD/Dubai": {"Single": 35, "Married": 45}, "AA": {"Single": 30, "Married": 40}},
                  "furniture_allowance_k_once": {"AD/Dubai": {"Single": 12, "Married": 15}, "AA": {"Single": 12, "Married": 15}},
                  "repatriation_allowance": 2000},
    "Instructor": {"annual_leave_days": 42, "joining_ticket_international": "1+1+2 Economy",
                  "housing_allowance_k": {"AD/Dubai": {"Single": 35, "Married": 45}, "AA": {"Single": 30, "Married": 40}},
                  "furniture_allowance_k_once": {"AD/Dubai": {"Single": 12, "Married": 15}, "AA": {"Single": 12, "Married": 15}},
                  "repatriation_allowance": 2000},
}

def campus_key(campus: str) -> str:
    return "AD/Dubai" if campus in ["Abu Dhabi", "Dubai", "AD/Dubai"] else "AA"

def fmt_amt(n: int) -> str: return f"{int(n):,}"

def compute_benefits_mapping(rank: str, marital: str, campus: str, is_international: bool):
    R = BENEFITS[rank]; S = BENEFITS["_shared"]; ckey = campus_key(campus)
    housing = R["housing_allowance_k"][ckey][marital] * 1000
    furniture = R["furniture_allowance_k_once"][ckey][marital] * 1000
    edu = S["children_school_allowance"][ckey]
    join = R["joining_ticket_international"] if is_international else ""
    return {
        "HOUSING_ALLOWANCE": fmt_amt(housing),
        "FURNITURE_ALLOWANCE": fmt_amt(furniture),
        "JOINING_TICKET": join,
        "REPARIATION_ALLOWANCE": fmt_amt(R["repatriation_allowance"]),
        "ANNUAL_LEAVE_DAYS": R["annual_leave_days"],
        "EDUCATION_ALLOWANCE_PER_CHILD": fmt_amt(edu),
        "EDUCATION_ALLOWANCE_TOTAL": fmt_amt(edu),
    }

# --- docx helpers ---
def _set_paragraph_text(par, text: str):
    for _ in range(len(par.runs)):
        par.runs[0].text = ""
        del par.runs[0]
    par.add_run(text)

def _insert_paragraph_after(paragraph, text):
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    p = paragraph._parent.add_paragraph()
    p._p = new_p
    _set_paragraph_text(p, text)
    return p

# Robust regex replacer: handles {{ KEY }} with any spaces or run breaks
def _regex_replace(text: str, mapping: dict) -> str:
    for k, v in mapping.items():
        # collapse any stray spaces inside braces, tolerate line/run breaks
        pattern = re.compile(r"\{\{\s*" + re.escape(k) + r"\s*\}\}")
        text = pattern.sub(str(v), text)
    return text

def rebuild_benefits_section(doc: Document, mapping: dict):
    start_idx = end_idx = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t.startswith("3. Benefits"): start_idx = i
        elif start_idx is not None and t.startswith("4."): end_idx = i; break
    if start_idx is None: return
    if end_idx is None: end_idx = len(doc.paragraphs)
    for i in range(end_idx - 1, start_idx, -1):
        doc.paragraphs[i]._element.getparent().remove(doc.paragraphs[i]._element)

    lines = [
        f"Accommodation: Unfurnished on-campus accommodation based on availability, or a housing allowance of AED {mapping['HOUSING_ALLOWANCE']} per year (paid monthly) will be provided based on eligibility.",
        f"Furniture Allowance: AED {mapping['FURNITURE_ALLOWANCE']} provided at the commencement of employment as a forgivable loan amortized over three (3) years. Should you leave ADU before completing three years of service, the amount will be repayable on a pro-rata basis.",
        "Annual Leave Airfare: Cash in lieu of economy class air tickets for yourself, your spouse, and up to two (2) eligible dependent children under the age of 21 years residing in the UAE, based on ADU’s published schedule of rates including your country of origin. This amount will be paid annually in the month of May, prorated to your joining date.",
    ]
    if mapping.get("JOINING_TICKET"):
        lines.append(f"Commencement Air Tickets: {mapping['JOINING_TICKET']}")
    lines += [
        "Repatriation Air Tickets: You will be provided with Economy Class air tickets for yourself, spouse and your eligible dependents (up to 2 children under 21 years) residing in the UAE upon your end of employment to your country of origin.",
        f"Repatriation Allowance: AED {mapping['REPARIATION_ALLOWANCE']} upon conclusion of your contract, applicable only upon completion of two (2) years of continuous service with ADU.",
        "Medical Insurance: You will be provided with medical insurance coverage for yourself, spouse and your eligible dependents (up to 3 children under 21 years) residing in the UAE. (Applicable only for married individuals with spouse/children under their sponsorship)",
        f"Annual Leave Entitlement: {mapping['ANNUAL_LEAVE_DAYS']} calendar days of paid annual leave.",
        f"School Fee Subsidy: An annual subsidy of AED {mapping['EDUCATION_ALLOWANCE_PER_CHILD']} per eligible child under the age of 21 years residing in the UAE under your sponsorship, up to a maximum of AED {mapping['EDUCATION_ALLOWANCE_TOTAL']} per family. This benefit applies only to married individuals with children under their sponsorship.",
        "ADU Tuition Waiver: 75% deduction on tuition fees for self, 50% for dependents and 25% for immediate family in accordance with ADU Policy. (applicable upon completion of one year of service with ADU)",
    ]
    anchor = doc.paragraphs[start_idx]
    _set_paragraph_text(anchor, "3. Benefits")
    last = anchor
    for line in lines: last = _insert_paragraph_after(last, line)

# Remove paragraphs still containing unreplaced tokens, or raw-value-only lines; keep last of key policy paras
TOKEN_PATTERN = re.compile(r"\{\{[^}]+\}\}")

KEEP_LAST_STARTS = [
    "Abu Dhabi University (ADU) is pleased",
    "Your first day of employment",
    "Probation Period:",
    "Notice Period:",
    "Your total monthly compensation will be AED",
]

def cleanup_after_replacement(doc: Document, mapping: dict):
    # delete any paragraph that STILL contains {{...}}
    for p in list(doc.paragraphs):
        if TOKEN_PATTERN.search(p.text):
            p._element.getparent().remove(p._element)

    # delete raw-value-only lines (e.g., 'Dr. Dana', 'Dana', '+971…')
    raw_values = {str(mapping[k]).strip() for k in mapping if k in {
        "SALUTATION","CANDIDATE_NAME","TELEPHONE","PERSONAL_EMAIL",
        "ID","DATE","POSITION","DEPARTMENT","CAMPUS","REPORTING_MANAGER","SALARY","PROBATION"
    } and mapping.get(k) not in (None, "")}
    for p in list(doc.paragraphs):
        if p.text.strip() in raw_values:
            p._element.getparent().remove(p._element)

    # keep only the LAST occurrence of key policy lines
    last = {}
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        for s in KEEP_LAST_STARTS:
            if t.startswith(s):
                last[s] = i
    for s, keep in last.items():
        for i, p in enumerate(list(doc.paragraphs)):
            if i < keep and p.text.strip().startswith(s):
                p._element.getparent().remove(p._element)

def replace_placeholders(doc: Document, mapping: dict):
    # Replace in all paragraphs
    for p in doc.paragraphs:
        _set_paragraph_text(p, _regex_replace(p.text, mapping))
    # Replace in tables too
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _set_paragraph_text(p, _regex_replace(p.text, mapping))

    rebuild_benefits_section(doc, mapping)
    cleanup_after_replacement(doc, mapping)

def generate_docx(template_bytes: bytes | None, mapping: dict) -> bytes:
    doc = Document(BytesIO(template_bytes)) if template_bytes else Document(DEFAULT_TEMPLATE_PATH)
    replace_placeholders(doc, mapping)
    out = BytesIO(); doc.save(out); out.seek(0); return out.getvalue()

# ---------- UI ----------
st.title("📄 ADU – Faculty Offer Letter Generator")
with st.form("offer_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        candidate_id = st.text_input("ID (Ref)")
        salutation = st.selectbox("Salutation", ["Dr.", "Mr.", "Ms.", "Prof.", "Eng."])
        candidate_name = st.text_input("Candidate Name")
        telephone = st.text_input("Telephone")
        personal_email = st.text_input("Personal Email")
    with c2:
        position = st.text_input("Position")
        department = st.text_input("Department")
        reporting_manager = st.text_input("Reporting Manager’s Title")
        campus = st.selectbox("Campus", ["Abu Dhabi", "Dubai", "Al Ain"])
        salary = st.number_input("Total Monthly Compensation (AED)", min_value=0, step=500, value=0)

    c3, c4, c5, c6 = st.columns(4)
    with c3:
        rank = st.selectbox("Rank", [k for k in BENEFITS if k != "_shared"])
    with c4:
        marital_status = st.selectbox("Marital Status", ["Single", "Married"])
    with c5:
        hire_type = st.selectbox("Hire Type", ["Local", "International"])
    with c6:
        probation = st.number_input("Probation (months)", min_value=1, max_value=12, value=6)

    uploaded_template = st.file_uploader("Upload custom DOCX (optional)", type=["docx"])
    submit = st.form_submit_button("Generate Offer Letter")

if submit:
    today = datetime.now().strftime(DATE_FORMAT)
    base_map = {
        "ID": candidate_id, "DATE": today, "SALUTATION": salutation, "CANDIDATE_NAME": candidate_name,
        "TELEPHONE": telephone, "PERSONAL_EMAIL": personal_email, "POSITION": position,
        "DEPARTMENT": department, "CAMPUS": campus, "REPORTING_MANAGER": reporting_manager,
        "SALARY": f"{int(salary):,}" if salary else "", "PROBATION": probation,
    }
    benefits_map = compute_benefits_mapping(rank, marital_status, campus, hire_type == "International")
    mapping = {**base_map, **benefits_map}
    tpl_bytes = uploaded_template.read() if uploaded_template else None
    try:
        docx_bytes = generate_docx(tpl_bytes, mapping)
        st.success("Offer letter generated successfully.")
        st.download_button("⬇️ Download Offer Letter (DOCX)", docx_bytes,
                           file_name=f"Offer_{(candidate_name or 'Candidate').replace(' ', '_')}.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        st.error(f"Generation failed: {e}")
