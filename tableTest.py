import sys
import fitz
import pdfplumber
import json
import os

fname = sys.argv[1]
section_keyword = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "COURSEWORK", "LINKS"]

# Output JSON file name
base_name = os.path.splitext(os.path.basename(fname))[0]
json_output = f"{base_name}_parsed.json"

# Open with pdfplumber for table extraction
with pdfplumber.open(fname) as plumber_pdf:
    # Open with fitz for text extraction
    with fitz.open(fname) as doc:

        current_section = None
        sections = {}
        para_font = {}
        para_size = {}
        unique_font = set()
        unique_size = set()

        for page_index, page in enumerate(doc):
            page_width = page.rect.width
            midpoint = page_width / 2
            text_dict = page.get_text("dict")

            sorted_blocks = sorted(
                text_dict["blocks"],
                key=lambda b: (b["bbox"][1], b["bbox"][0])
            )

            for block in sorted_blocks:
                if block["type"] == 0:  # text block
                    prev_y1 = None
                    paragraph_lines = []
                    for line in block["lines"]:
                        line_text = ""
                        max_size = 0
                        span_font = ""
                        threshold = 10

                        for span in line["spans"]:
                            line_text += span["text"]
                            size = span["size"]
                            if max_size < size:
                                max_size = size
                                span_font = span["font"]

                        line_y0 = line["bbox"][1]
                        line_y1 = line["bbox"][3]
                        is_heading = False

                        upper_text = line_text.upper()
                        for keyword in section_keyword:
                            if keyword in upper_text:
                                current_section = keyword
                                is_heading = True
                                break

                        if current_section is None and not is_heading:
                            if ("Bold" in span_font and max_size > 15):
                                current_section = "header"
                            elif ("Bold" in span_font and max_size < 15):
                                current_section = "Section heading"
                            elif (not "Bold" in span_font and max_size < 15):
                                current_section = "Body"

                        if span_font not in para_font:
                            para_font[span_font] = []
                        para_font[span_font].append(span_font)
                        unique_font.add(span_font)

                        if max_size not in para_size:
                            para_size[max_size] = []
                        para_size[max_size].append(max_size)
                        unique_size.add(max_size)

                        if prev_y1 is None:
                            paragraph_lines = [line_text]
                        elif line_y0 - prev_y1 < threshold:
                            paragraph_lines.append(line_text)
                        else:
                            if current_section not in sections:
                                sections[current_section] = []
                            sections[current_section].append(" ".join(paragraph_lines))
                            paragraph_lines = []

                        prev_y1 = line_y1

                    if paragraph_lines:
                        if current_section not in sections:
                            sections[current_section] = []
                        sections[current_section].append(" ".join(paragraph_lines))
                        paragraph_lines = []

            # ----- Table Extraction -----
            plumber_page = plumber_pdf.pages[page_index]
            page_tables = plumber_page.extract_tables()

            if page_tables:
                if "TABLES" not in sections:
                    sections["TABLES"] = []
                for table in page_tables:
                    sections["TABLES"].append(table)

# Save to JSON
with open(json_output, "w", encoding="utf-8") as f:
    json.dump(sections, f, ensure_ascii=False, indent=4)

print(f"✅ Data extracted and saved to {json_output}")
