import sys
import fitz
import pdfplumber
import json
import os
import re

DATE_PATTERN = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s.-]?\d{4}|(?:19|20)\d{2}|Present|Current|NOW)"

def clean_text(text):
    if not text: return ""
    text = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219]', '', text)
    return " ".join(text.split())

def is_inside_table(text_bbox, table_bboxes, tolerance=3):
    tx0, ty0, tx1, ty1 = text_bbox
    for (bx0, by0, bx1, by1) in table_bboxes:
        if (tx0 >= bx0 - tolerance and ty0 >= by0 - tolerance and 
            tx1 <= bx1 + tolerance and ty1 <= by1 + tolerance):
            return True
    return False

def extract_name_by_font(doc):
    page = doc[0]
    text_dict = page.get_text("dict")
    max_size = 0
    likely_name = "Unknown"
    for block in text_dict["blocks"]:
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    size = span["size"]
                    if len(text) > 1 and not text.isdigit():
                        if size > max_size:
                            max_size = size
                            likely_name = text
    return likely_name

def structure_experience_section(experience_list):
    structured_jobs = []
    
    line_buffer = []
    
    current_job = None

    for line in experience_list:
        if re.search(DATE_PATTERN, line, re.IGNORECASE):
            
            job_title_part = []
            description_part = []
            
            while line_buffer:
                candidate = line_buffer.pop()
                if len(candidate.split()) < 10:
                    job_title_part.insert(0, candidate)
                else:
                    description_part.insert(0, candidate)
                    break 

            if current_job:
                current_job["details"].extend(description_part)
                current_job["details"].extend(line_buffer)
                structured_jobs.append(current_job)
            
            full_header = " | ".join(job_title_part + [line])
            current_job = {"header": full_header, "details": []}
            
            line_buffer = []

        else:
            line_buffer.append(line)
            
    if current_job:
        current_job["details"].extend(line_buffer)
        structured_jobs.append(current_job)
        
    return structured_jobs

def extract_entities(text_content):
    entities = {"email": None, "phone": None, "links": []}
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text_content)
    if email_match: entities["email"] = email_match.group(0)
    phone_match = re.search(r'\(?\+?[0-9]{1,3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}', text_content)
    if phone_match: entities["phone"] = phone_match.group(0)
    links = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', text_content)
    entities["links"] = links
    return entities

def main():
    if len(sys.argv) < 2:
        print("Usage: python parser_v3.py <path_to_resume.pdf>")
        sys.exit(1)

    fname = sys.argv[1]
    section_keywords = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "COURSEWORK", "LINKS", "SUMMARY", "CERTIFICATIONS", "EXPERTISE", "ABOUT ME"]

    final_data = {
        "metadata": {"filename": fname, "name": ""},
        "entities": {},
        "sections": {},
        "tables": []
    }
    
    page_table_bboxes = {}
    try:
        with pdfplumber.open(fname) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                table_objects = page.find_tables()
                if tables:
                    for table in tables:
                        final_data["tables"].append({"page": i + 1, "data": table})
                bboxes = []
                if table_objects:
                    for t in table_objects: bboxes.append(t.bbox)
                page_table_bboxes[i] = bboxes
    except Exception:
        pass

    with fitz.open(fname) as doc:
        final_data["metadata"]["name"] = extract_name_by_font(doc)
        current_section = "CONTACT_INFO"
        final_data["sections"][current_section] = []
        
        for page_index, page in enumerate(doc):
            text_dict = page.get_text("dict")
            blocks = text_dict["blocks"]
            current_page_table_areas = page_table_bboxes.get(page_index, [])

            for block in blocks:
                if block["type"] == 0:
                    if is_inside_table(block["bbox"], current_page_table_areas):
                        continue

                    paragraph_lines = []
                    for line in block["lines"]:
                        line_text = ""
                        max_size = 0
                        span_font = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                            size = span["size"]
                            if size > max_size:
                                max_size = size
                                span_font = span["font"]
                        
                        clean_line = line_text.strip()
                        if not clean_line: continue

                        upper_text = clean_line.upper()
                        is_heading = False
                        
                        for keyword in section_keywords:
                            if (keyword == upper_text) or (keyword in upper_text and len(clean_line.split()) < 5):
                                current_section = keyword
                                is_heading = True
                                break
                        
                        if is_heading:
                            if current_section not in final_data["sections"]:
                                final_data["sections"][current_section] = []
                        else:
                            paragraph_lines.append(clean_line)

                    if paragraph_lines:
                        full_para = " ".join(paragraph_lines)
                        full_para = clean_text(full_para)
                        final_data["sections"][current_section].append(full_para)

    combined_text = " ".join(final_data["sections"].get("CONTACT_INFO", []))
    if len(combined_text) < 10 and "CONTACT" in final_data["sections"]:
         combined_text += " ".join(final_data["sections"]["CONTACT"])
    
    if len(combined_text) < 10:
        first_key = list(final_data["sections"].keys())[0]
        combined_text += " ".join(final_data["sections"][first_key][:5])
        
    final_data["entities"] = extract_entities(combined_text)

    if "EXPERIENCE" in final_data["sections"]:
        final_data["sections"]["EXPERIENCE"] = structure_experience_section(final_data["sections"]["EXPERIENCE"])
        
    if "WORK EXPERIENCE" in final_data["sections"]:
        final_data["sections"]["WORK EXPERIENCE"] = structure_experience_section(final_data["sections"]["WORK EXPERIENCE"])

    if "EDUCATION" in final_data["sections"]:
        final_data["sections"]["EDUCATION"] = structure_experience_section(final_data["sections"]["EDUCATION"])

    base_name = os.path.splitext(os.path.basename(fname))[0]
    json_output = f"{base_name}_v3_parsed.json"
    
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"Parser V3 (Look-back Enabled) Complete. Saved to {json_output}")

if __name__ == "__main__":
    main()