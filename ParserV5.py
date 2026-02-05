import sys
import fitz
import json
import os
import re

COLUMN_GAP_THRESHOLD = 20 
HEADER_Y_LIMIT = 120

DATE_PATTERN = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s.-]?\d{4}|(?:19|20)\d{2}|Present|Current|NOW)"

def clean_text(text):
    if not text: return ""
    return re.sub(r'[\u2022\u2023\u25E6\u2043\u2219]', '', text).strip()

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

def sort_blocks_by_columns(blocks, page_width):
    header_blocks = []
    left_col = []
    right_col = []
    mid_point = page_width / 2
    
    for b in blocks:
        x0, y0, x1, y1 = b["bbox"]
        center_x = (x0 + x1) / 2
        
        if y1 < HEADER_Y_LIMIT:
            header_blocks.append(b)
        
        elif center_x < mid_point:
            left_col.append(b)
        else:
            right_col.append(b)

    header_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    left_col.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    right_col.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

    return header_blocks + left_col + right_col

def structure_experience_section(experience_list):
    structured_jobs = []
    line_buffer = []
    current_job = None

    for line in experience_list:
        clean = line.strip()
        if not clean: continue
        
        if re.search(DATE_PATTERN, clean, re.IGNORECASE):
            
            header_part = []
            desc_part = []
            
            while line_buffer:
                candidate = line_buffer.pop()
                if len(candidate.split()) < 10:
                    header_part.insert(0, candidate)
                else:
                    desc_part.insert(0, candidate)
                    break
            
            if current_job:
                current_job["details"].extend(desc_part)
                current_job["details"].extend(line_buffer)
                structured_jobs.append(current_job)
            
            full_header = " | ".join(header_part + [clean])
            current_job = {"header": full_header, "details": []}
            line_buffer = []
        else:
            line_buffer.append(clean)
            
    if current_job:
        current_job["details"].extend(line_buffer)
        structured_jobs.append(current_job)
        
    return structured_jobs

def extract_entities(text_content):
    entities = {"email": None, "phone": None, "links": []}
    
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text_content)
    if email_match: entities["email"] = email_match.group(0)

    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phone_match = re.search(phone_pattern, text_content)
    if phone_match: entities["phone"] = phone_match.group(0)

    links = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', text_content)
    entities["links"] = links
    return entities

def main():
    if len(sys.argv) < 2:
        print("Usage: python ParserV5.py <path_to_resume.pdf>")
        sys.exit(1)

    fname = sys.argv[1]
    
    section_keywords = [
        "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE", "SKILLS", 
        "PROJECTS", "LINKS", "SUMMARY", "CERTIFICATIONS", 
        "EXPERTISE", "ABOUT ME", "CONTACT", "REFERENCE"
    ]

    final_data = {
        "metadata": {"filename": fname, "name": ""},
        "entities": {},
        "sections": {},
    }

    with fitz.open(fname) as doc:
        final_data["metadata"]["name"] = extract_name_by_font(doc)
        current_section = "UNLABELED"
        
        for page in doc:
            page_width = page.rect.width
            text_dict = page.get_text("dict")
            raw_blocks = text_dict["blocks"]
            
            sorted_blocks = sort_blocks_by_columns(raw_blocks, page_width)

            for block in sorted_blocks:
                if block["type"] == 0: 
                    
                    for line in block["lines"]:
                        line_parts = []
                        current_part_text = ""
                        
                        spans = line["spans"]
                        for i, span in enumerate(spans):
                            text = span["text"]
                            current_part_text += text
                            
                            if i < len(spans) - 1:
                                next_span = spans[i+1]
                                gap = next_span["bbox"][0] - span["bbox"][2]
                                if gap > COLUMN_GAP_THRESHOLD:
                                    if current_part_text.strip():
                                        line_parts.append(current_part_text.strip())
                                    current_part_text = ""
                        
                        if current_part_text.strip():
                            line_parts.append(current_part_text.strip())

                        for part in line_parts:
                            clean_part = clean_text(part)
                            upper_text = clean_part.upper()
                            
                            is_heading = False
                            for keyword in section_keywords:
                                if upper_text == keyword: 
                                    current_section = keyword
                                    is_heading = True
                                    break
                            
                            if is_heading:
                                if current_section not in final_data["sections"]:
                                    final_data["sections"][current_section] = []
                            else:
                                if current_section not in final_data["sections"]:
                                    final_data["sections"][current_section] = []
                                final_data["sections"][current_section].append(clean_part)

    for sec in ["EXPERIENCE", "WORK EXPERIENCE", "EDUCATION"]:
        if sec in final_data["sections"]:
            final_data["sections"][sec] = structure_experience_section(final_data["sections"][sec])

    contact_source = []
    if "CONTACT" in final_data["sections"]:
        contact_source += final_data["sections"]["CONTACT"]
    if "UNLABELED" in final_data["sections"]:
        contact_source += final_data["sections"]["UNLABELED"][:15]
        
    final_data["entities"] = extract_entities(" ".join(contact_source))

    base_name = os.path.splitext(os.path.basename(fname))[0]
    json_output = f"{base_name}_v5_parsed.json"
    
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"Parser V5 Complete. Saved to {json_output}")

if __name__ == "__main__":
    main()