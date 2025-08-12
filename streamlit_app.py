import re
import streamlit as st
from docx import Document
from io import BytesIO
from datetime import datetime
from docx.oxml import OxmlElement

st.set_page_config(page_title="ADU Faculty Contract Generator", page_icon="📄", layout="centered")

DEFAULT_TEMPLATE_PATH = "Faculty_Offer_Letter_Template_Placeholders.docx"
DATE_FORMAT = "%d %B %Y"  # e.g., 12 August 2025

# ===== BENEFITS (only the 7 fields you require) =====
BENEFITS = {
    "_shared": {"children_school_allowance": {"AD/Dubai": 60000, "AA": 50000}},
    "Professor": {
        "annual_leave_days": 56, "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
        "repatriation_allowance": 3000,
    },
    "Associate / Sr. Lecturer": {
        "annual_leave_days": 56, "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
        "repatriation_allowance": 3000,
    },
    "Assistant / Lecturer": {
        "annual_leave_days": 56, "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 45, "Married": 60}, "AA": {"Single": 35, "Married": 45}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 20, "Married": 30}, "AA": {"Single": 20, "Married": 30}},
        "repatriation_allowance": 3000,
    },
    "Senior Instructor": {
        "annual_leave_days": 42, "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 35, "Married": 45}, "AA": {"Single": 30, "Married": 40}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 12, "Married": 15}, "AA": {"Single": 12, "Married": 15}},
        "repatriation_allowance": 2000,
    },
    "Instructor": {
        "annual_leave_days": 42, "joining_ticket_international": "1+1+2 Economy",
        "housing_allowance_k": {"AD/Dubai": {"Single": 35, "Married": 45}, "AA": {"Single": 30, "Married": 40}},
        "furniture_allowance_k_once": {"AD/Dubai": {"Single": 12, "Married": 15}, "AA": {"Single": 12, "Married": 15}},
        "repatriation_allowance": 2000,
    },
}

# ========== helpers ==========
def campus_key(campus: str) -> str:
    # Dubai follows Abu Dhabi rules
    return "AD/Dubai" if campus in ("Abu Dhabi", "Dubai", "AD/Dubai") else "AA"

def fmt_amt(n: int) -> str:
    return f"{int(n):,}"

def compute_benefits_mapping(rank: str, marital: str, campus: str, is_international: bool):
    R = BENEFITS[rank]; S = BENEFITS["_shared"]; ckey = campus_key(campus)
    housing = R["housing_allowance_k"][ckey][marital] * 1000
    furniture = R["furniture_allowance_k_once"][ckey][marital] * 1000
    edu = S["children_school_allowance"][ckey]
    joining = R["joining_ticket_international"] if is_international else ""
    return {
        "HOUSING_ALLOWANCE": fmt_amt(housing),
        "FURNITURE_ALLOWANCE": fmt_amt(furniture),
        "JOINING_TICKET": joining,
        "REPARIATION_ALLOWANCE": fmt_amt(R["repatriation_allowance"]),
        "ANNUAL_LEAVE_DAYS": R["annual_leave_days"],
        "EDUCATION_ALLOWANCE_PER_CHILD": fmt_amt(edu),
        "EDUCATION_ALLOWANCE_TOTAL": fmt_amt(edu),
    }

# docx utils
TOKEN_ANY = re.compile(r"\{+\s*[^}]+\s*\}+")

def _set_paragraph_text(par, text: str):
    for _ in range(len(par.runs)):
        par.runs[0].text = ""
        del par.runs[0]
    par.add_run(text)

def _insert_paragraph_after(paragraph, text):
    new = OxmlElement("w:p"); paragraph._p.addnext(new)
    p = paragraph._parent.add_paragraph(); p._p = new
    _set_paragraph_text(p, text); return p

def _token_replace(text: str, mapping: dict) -> str:
    # Replace {{KEY}} or {KEY}, tolerant of spaces/run splits
    for k, v in mapping.items():
        text = re.sub(r"\{+\s*" + re.escape(k) + r"\s*\}+", str(v), text)
    return text

def purge_placeholder_paragraphs(doc: Document):
    # Remove any paragraph that still contains a token
    for p in list(doc.paragraphs):
        if ("{{" in p.text) or ("}}" in p.text) or TOKEN_ANY.search(p.text):
            p._element.getparent().remove(p._element)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in list(cell.paragraphs):
                    if ("{{" in p.text) or ("}}" in p.text) or TOKEN_ANY.search(p.text):
                        p._element.getparent().remove(p._element)

def normalize_header_intro_salary_terms(doc: Document, m: dict):
    # Ensure single clean Ref/Date/Tel/Email lines
    def keep_last_by_label(label_text: str, final_text: str):
        hits = [p for p in doc.paragraphs if label_text in p.text]
        if not hits: return
        keep = hits[-1]
        for p in hits[:-1]:
            p._element.getparent().remove(p._element)
        _set_paragraph_text(keep, final_text)

    keep_last_by_label("Ref:",  f"Ref: {m.get('ID','')}")
    keep_last_by_label("Date:", f"Date: {m.get('DATE','')}")
    keep_last_by_label("Tel No:", f"Tel No: {m.get('TELEPHONE','')}")
    keep_last_by_label("Email ID:", f"Email ID: {m.get('PERSONAL_EMAIL','')}")

    # Remove standalone "Salutation Name" line, keep only "Dear ..."
    sal = (m.get("SALUTATION","") + " " + m.get("CANDIDATE_NAME","")).strip()
    sal_variants = {sal, sal + ","}
    for p in list(doc.paragraphs):
        if p.text.strip() in sal_variants:
            p._element.getparent().remove(p._element)
    dear = f"Dear {sal},"
    dears = [p for p in doc.paragraphs if p.text.strip().startswith("Dear")]
    if dears:
        for p in dears[:-1]:
            p._element.getparent().remove(p._element)
        _set_paragraph_text(dears[-1], dear)

    # Intro sentence (keep last, exact text)
    intro = ("Abu Dhabi University (ADU) is pleased to offer you a contract of employment "
             f"for the position of {m.get('POSITION','')} in the {m.get('DEPARTMENT','')} "
             f"based in {m.get('CAMPUS','')}, UAE. This position reports to the "
             f"{m.get('REPORTING_MANAGER','')}.")
    intros = [p for p in doc.paragraphs if "Abu Dhabi University (ADU) is pleased" in p.text]
    if intros:
        for p in intros[:-1]:
            p._element.getparent().remove(p._element)
        _set_paragraph_text(intros[-1], intro)

    # Salary heading (keep last, exact text)
    salaries = [p for p in doc.paragraphs if "Your total monthly compensation" in p.text]
    if salaries:
        for p in salaries[:-1]:
            p._element.getparent().remove(p._element)
        _set_paragraph_text(salaries[-1],
            f"Your total monthly compensation will be AED {m.get('SALARY','')}, comprising:")

    # Keep only the last of these policy lines
    starts = ["Your first day of employment", "Probation Period:", "Notice Period:"]
    last = {}
    for p in doc.paragraphs:
        t = p.text.strip()
        for s in starts:
            if t.startswith(s): last[s] = p
    for s, keep_par in last.items():
        for p in list(doc.paragraphs):
            if p is keep_par: continue
            if p.text.strip().startswith(s):
                p._element.getparent().remove(p._element)

def rebuild_benefits_section(doc: Document, mapping: dict):
    # Find 3. Benefits .. next "4."
    start = end = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t.startswith("3. Benefits"): start = i
        elif start is not None and t.startswith("4."): end = i; break
    if start is None: return
    if end is None: end = len(doc.paragraphs)

    # Remove all lines after the header within the section
    to_remove = [doc.paragraphs[i]._element for i in range(start + 1, end)]
    for el in to_remove:
        el.getparent().remove(el)

    # Compose clean lines from 7 values
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

    # Ensure header text is correct and insert lines after it
    header = doc.paragraphs[start]
    _set_paragraph_text(header, "3. Benefits")
    last = header
    for line in lines:
        last = _insert_paragraph_after(last, line)

def replace_placeholders(doc: Document, mapping: dict):
    # 1) Replace tokens everywhere (tolerant of run splits)
    for p in doc.paragraphs:
        _set_paragraph_text(p, _token_replace(p.text, mapping))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _set_paragraph_text(p, _token_replace(p.text, mapping))

    # 2) Purge any paragraph that still contains a token -> kills green leftover lines
    purge_placeholder_paragraphs(doc)

    # 3) Normalize header/intro/salary/probation/notice to single clean copies
    normalize_header_intro_salary_terms(doc, mapping)

    # 4) Rebuild Benefits section cleanly from 7 values
    rebuild_benefits_section(doc, mapping)

def generate_docx(template_bytes: bytes | None, mapping: dict) -> bytes:
    doc = Document(BytesIO(template_bytes)) if template_bytes else Document(DEFAULT_TEMPLATE_PATH)
    replace_placeholders(doc, mapping)
    out = BytesIO(); doc.save(out); out.seek(0); return out.getvalue()

# ========== UI ==========
st.title("📄 ADU – Faculty Offer Letter Generator")

with st.form("offer_form", clear_on_submit=False):
    st.subheader("Candidate & Position")
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

    st.subheader("Contract Settings")
    c3, c4, c5, c6 = st.columns(4)
    with c3:
        rank = st.selectbox("Rank", [k for k in BENEFITS if k != "_shared"], index=2)
    with c4:
        marital_status = st.selectbox("Marital Status", ["Single", "Married"], index=0)
    with c5:
        hire_type = st.selectbox("Hire Type", ["Local", "International"], index=0)
    with c6:
        probation = st.number_input("Probation (months)", min_value=1, max_value=12, value=6)

    uploaded_template = st.file_uploader("Upload custom DOCX (optional). Otherwise uses default.", type=["docx"])
    submit = st.form_submit_button("Generate Offer Letter")

if submit:
    today = datetime.now().strftime(DATE_FORMAT)

    # 13 direct-input placeholders
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

    # 7 benefits placeholders
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
