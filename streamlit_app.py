import streamlit as st
from docx import Document
from io import BytesIO
import datetime

# -------------------------
# Benefits Mapping Function
# -------------------------
def compute_benefits_mapping(employment_category, marital_status, campus):
    # Treat Dubai as Abu Dhabi
    campus_key = campus
    if campus.lower() == "dubai":
        campus_key = "abu dhabi"

    # Example benefits table dictionary
    benefits_data = {
        ("assistant professor", "single", "abu dhabi"): {
            "HOUSING_ALLOWANCE": 45000,
            "FURNITURE_ALLOWANCE": 15000,
            "JOINING_TICKET": "1+1+2 Economy",
            "RELOCATION_ALLOWANCE": 3000,
            "REPATRIATION_TICKET": "1+1+2 Economy",
            "REPARIATION_ALLOWANCE": 2000,
            "HEALTH_INSURANCE": "1+1+3",
            "ANNUAL_LEAVE_DAYS": 42,
            "EDUCATION_ALLOWANCE_PER_CHILD": 30000,
            "EDUCATION_ALLOWANCE_TOTAL": 60000,
            "TUITION_EMPLOYEE": 75,
            "TUITION_DEPENDENT": 50,
            "TUITION_IMMEDIATE": 25
        },
        # Add other category/marital/campus combinations here
    }

    # Default mapping if not found
    mapping = benefits_data.get(
        (employment_category.lower(), marital_status.lower(), campus_key.lower()),
        {
            "HOUSING_ALLOWANCE": "N/A",
            "FURNITURE_ALLOWANCE": "N/A",
            "JOINING_TICKET": "",
            "RELOCATION_ALLOWANCE": "N/A",
            "REPATRIATION_TICKET": "1+1+2 Economy",
            "REPARIATION_ALLOWANCE": "N/A",
            "HEALTH_INSURANCE": "1+1+3",
            "ANNUAL_LEAVE_DAYS": "N/A",
            "EDUCATION_ALLOWANCE_PER_CHILD": "N/A",
            "EDUCATION_ALLOWANCE_TOTAL": "N/A",
            "TUITION_EMPLOYEE": "N/A",
            "TUITION_DEPENDENT": "N/A",
            "TUITION_IMMEDIATE": "N/A"
        }
    )

    # If local hire, remove commencement ticket only
    if employment_category.lower() in ["assistant professor", "associate professor", "professor"]:
        if st.session_state.get("hire_type", "local") == "local":
            mapping["JOINING_TICKET"] = ""

    return mapping


# -------------------------
# Compose Benefits Block
# -------------------------
def compose_benefits_block(m):
    join_line = f"- Commencement Air Tickets: {m['JOINING_TICKET']}\n" if m.get("JOINING_TICKET") else ""
    return (
        f"- Accommodation: Unfurnished on-campus accommodation based on availability, or a housing allowance of AED {m['HOUSING_ALLOWANCE']} per year (paid monthly) will be provided based on eligibility.\n"
        f"- Furniture Allowance: AED {m['FURNITURE_ALLOWANCE']} provided at the commencement of employment as a forgivable loan amortized over three (3) years. Should you leave ADU before completing three years of service, the amount will be repayable on a pro-rata basis.\n"
        "- Annual Leave Airfare: Cash in lieu of economy class air tickets for yourself, your spouse, and up to two (2) eligible dependent children under the age of 21 years residing in the UAE, based on ADU’s published schedule of rates including your country of origin. This amount will be paid annually in the month of May, prorated to your joining date.\n"
        f"{join_line}"
        f"- Relocation Allowance: Up to AED {m['RELOCATION_ALLOWANCE']} at the commencement of employment to support the relocation of personal effects to ADU-provided accommodation. Reimbursement will be subject to submission of original receipts.\n"
        f"- Repatriation Air Tickets: {m['REPATRIATION_TICKET']}\n"
        f"- Repatriation Allowance: AED {m['REPARIATION_ALLOWANCE']} upon conclusion of your contract, applicable only upon completion of two (2) years of continuous service with ADU.\n"
        f"- Medical Insurance: {m['HEALTH_INSURANCE']}\n"
        f"- Annual Leave Entitlement: {m['ANNUAL_LEAVE_DAYS']} calendar days of paid annual leave.\n"
        f"- School Fee Subsidy: An annual subsidy of AED {m['EDUCATION_ALLOWANCE_PER_CHILD']} per eligible child under the age of 21 years residing in the UAE under your sponsorship, up to a maximum of AED {m['EDUCATION_ALLOWANCE_TOTAL']} per family. This benefit applies only to married individuals with children under their sponsorship.\n"
        f"- ADU Tuition Waiver: {m['TUITION_EMPLOYEE']}% tuition fee deduction for yourself, {m['TUITION_DEPENDENT']}% for dependents, and {m['TUITION_IMMEDIATE']}% for immediate family members, in accordance with ADU policy. This benefit is applicable upon completion of one (1) year of service."
    )


# -------------------------
# Streamlit UI
# -------------------------
st.title("📄 ADU Faculty Offer Letter Generator")

with st.form("offer_form"):
    candidate_id = st.text_input("Candidate ID")
    name = st.text_input("Candidate Name")
    salutation = st.selectbox("Salutation", ["Dr.", "Mr.", "Ms."])
    telephone = st.text_input("Telephone Number")
    personal_email = st.text_input("Personal Email")
    position = st.text_input("Position Title")
    department = st.text_input("College/Department Name")
    campus = st.selectbox("Campus", ["Abu Dhabi", "Al Ain", "Dubai"])
    reporting_manager = st.text_input("Reporting Manager’s Title")
    salary = st.number_input("Total Monthly Salary (AED)", min_value=0)
    probation = st.number_input("Probation Period (months)", min_value=0)
    employment_category = st.text_input("Employment Category (e.g., Assistant Professor)")
    marital_status = st.selectbox("Marital Status", ["Single", "Married"])
    hire_type = st.selectbox("Hire Type", ["International", "Local"])
    st.session_state["hire_type"] = hire_type

    submitted = st.form_submit_button("Generate Offer Letter")

if submitted:
    # Benefits mapping
    benefits_map = compute_benefits_mapping(employment_category, marital_status, campus)
    benefits_map["BENEFITS_BLOCK"] = compose_benefits_block(benefits_map)

    # Placeholder mapping
    mapping = {
        "ID": candidate_id,
        "NAME": name,
        "SALUTATION": salutation,
        "TELEPHONE": telephone,
        "EMAIL": personal_email,
        "POSITION": position,
        "DEPARTMENT": department,
        "CAMPUS": campus,
        "REPORTING_MANAGER": reporting_manager,
        "SALARY": f"{salary:,.2f}",
        "PROBATION": probation,
        **benefits_map
    }

    # Load template and replace
    template_path = "Faculty_Offer_Letter_Template_BenefitsBlock.docx"
    doc = Document(template_path)
    for p in doc.paragraphs:
        for key, value in mapping.items():
            if f"{{{{{key}}}}}" in p.text:
                inline = p.runs
                for i in range(len(inline)):
                    if f"{{{{{key}}}}}" in inline[i].text:
                        inline[i].text = inline[i].text.replace(f"{{{{{key}}}}}", str(value))

    # Save to BytesIO
    output = BytesIO()
    doc.save(output)
    output.seek(0)

    st.download_button(
        label="📥 Download Offer Letter",
        data=output,
        file_name=f"Offer_Letter_{name.replace(' ', '_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
