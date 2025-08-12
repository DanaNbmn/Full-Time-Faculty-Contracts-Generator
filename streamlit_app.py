def replace_placeholders(doc: Document, mapping: dict):
    """
    1) Replace placeholders in all paragraphs/cells.
    2) If JOINING_TICKET is empty, remove the 'Commencement Air Tickets:' paragraph.
    3) De-duplicate lines that appear twice in the same paragraph (keep the last).
    """
    # Sentences we guard against being duplicated in a single paragraph
    # (start anchors so we can cut the paragraph to the last occurrence)
    DEDUP_STARTS = [
        "Abu Dhabi University (ADU) is pleased",   # intro line
        "Probation Period:",                        # probation line
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
        # If a key phrase appears more than once, keep from its LAST occurrence onward
        for start in DEDUP_STARTS:
            idx = text.find(start)
            if idx != -1:
                last = text.rfind(start)
                if last != idx:  # appears at least twice
                    text = text[last:]
        return text

    def replace_and_clean(par):
        text = par.text

        # 1) Replace placeholders
        for k, v in mapping.items():
            token = f"{{{{{k}}}}}"
            if token in text:
                text = text.replace(token, str(v))

        # 2) Remove the entire Commencement line if JOINING_TICKET is blank
        if mapping.get("JOINING_TICKET", "") == "" and "Commencement Air Tickets:" in text:
            text = ""  # clear this paragraph completely

        # 3) De-duplicate if paragraph accidentally contains doubled content
        text = dedup_line(text)

        # Rebuild runs cleanly
        for _ in range(len(par.runs)):
            par.runs[0].text = ""
            del par.runs[0]
        if text:
            par.add_run(text)
        else:
            # If empty, leave as empty paragraph (Word keeps structure ok)
            par.add_run("")

    # Apply to all paragraphs
    for p in doc.paragraphs:
        replace_and_clean(p)

    # Apply to all table cells too (if any exist)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_and_clean(p)
