import sys
import fitz
import json
import os
import re

DATE_PATTERN = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s.-]?\d{4}|(?:19|20)\d{2}|\bPresent\b|\bCurrent\b|\bNOW\b)"

SECTION_KEYWORDS = [
    "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE", "SKILLS", 
    "PROJECTS", "LINKS", "SUMMARY", "CERTIFICATIONS", 
    "EXPERTISE", "ABOUT ME", "CONTACT", "REFERENCE", "REFERENCES", 
    "PROFILE", "LANGUAGE", "LANGUAGES", "HISTORY"
]

def clean_text(text):
    if not text: return ""
    text = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219]', '', text)
    return " ".join(text.split())

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
    elif line_buffer:
        structured_jobs.append({"header": "Misplaced Content", "details": line_buffer})
        
    return structured_jobs

def main():
    if len(sys.argv) < 2:
        print("Usage: python parser_v8.py <path_to_resume.pdf>")
        sys.exit(1)

    fname = sys.argv[1]
    final_data = {
        "metadata": {"filename": fname, "name": ""},
        "entities": {},
        "sections": {},
    }

    with fitz.open(fname) as doc:
        final_data["metadata"]["name"] = extract_name_by_font(doc)
        
        all_lines = []
        headers = [] 
        
        for page_idx, page in enumerate(doc):
            page_midpoint = page.rect.width / 2
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if block["type"] == 0:
                    for line in block["lines"]:
                        x0, y0, x1, y1 = line["bbox"]
                        
                        spans = line["spans"]
                        current_segment = ""
                        seg_x0 = x0
                        
                        for i, span in enumerate(spans):
                            txt = span["text"]
                            if not txt.strip(): continue
                            
                            if i > 0:
                                prev_span = spans[i-1]
                                gap = span["bbox"][0] - prev_span["bbox"][2]
                                
                                if gap > 15: 
                                    clean = clean_text(current_segment)
                                    if clean:
                                        seg_obj = {
                                            "text": clean,
                                            "bbox": (seg_x0, y0, prev_span["bbox"][2], y1),
                                            "page": page_idx,
                                            "midpoint": page_midpoint
                                        }
                                        all_lines.append(seg_obj)
                                        
                                        upper = clean.upper()
                                        for kw in SECTION_KEYWORDS:
                                            if upper == kw or upper.startswith(kw + " "):
                                                headers.append({**seg_obj, "keyword": kw})
                                                break
                                    
                                    current_segment = ""
                                    seg_x0 = span["bbox"][0]
                            
                            current_segment += txt
                        
                        clean = clean_text(current_segment)
                        if clean:
                            seg_obj = {
                                "text": clean,
                                "bbox": (seg_x0, y0, x1, y1),
                                "page": page_idx,
                                "midpoint": page_midpoint
                            }
                            all_lines.append(seg_obj)
                            
                            upper = clean.upper()
                            for kw in SECTION_KEYWORDS:
                                if upper == kw or upper.startswith(kw + " "):
                                    headers.append({**seg_obj, "keyword": kw})
                                    break

        sections_raw = {}
        
        for line in all_lines:
            is_header = False
            for h in headers:
                if h["bbox"] == line["bbox"] and h["text"] == line["text"]:
                    is_header = True
                    break
            if is_header: continue
            
            best_header = None
            min_vertical_dist = float('inf')
            
            line_x0, _, line_x1, line_y0 = line["bbox"]
            line_center_x = (line_x0 + line_x1) / 2
            midpoint = line["midpoint"]
            
            for header in headers:
                if header["page"] != line["page"]: continue
                
                h_x0, _, h_x1, h_y1 = header["bbox"]
                
                if h_y1 > line_y0: continue
                
                header_center = (h_x0 + h_x1) / 2
                same_column = False
                
                if header_center < midpoint and line_center_x < midpoint:
                    same_column = True
                elif header_center >= midpoint and line_center_x >= midpoint:
                    same_column = True
                elif (h_x1 - h_x0) > (midpoint * 1.5):
                    same_column = True
                    
                if same_column:
                    dist = line_y0 - h_y1
                    if dist < min_vertical_dist:
                        min_vertical_dist = dist
                        best_header = header["keyword"]

            target_section = best_header if best_header else "UNLABELED"
            
            if target_section not in sections_raw:
                sections_raw[target_section] = []
            sections_raw[target_section].append(line["text"])

    for sec in ["EXPERIENCE", "WORK EXPERIENCE", "EDUCATION", "HISTORY"]:
        if sec in sections_raw:
            final_data["sections"][sec] = structure_experience_section(sections_raw[sec])
            
    for sec, lines in sections_raw.items():
        if sec not in final_data["sections"]:
            final_data["sections"][sec] = lines

    contact_pool = []
    if "CONTACT" in final_data["sections"]: contact_pool += final_data["sections"]["CONTACT"]
    if "UNLABELED" in final_data["sections"]: contact_pool += final_data["sections"]["UNLABELED"][:12]
    
    final_data["entities"] = extract_entities(" ".join(contact_pool))

    base_name = os.path.splitext(os.path.basename(fname))[0]
    json_output = f"{base_name}_v6_parsed.json"
    
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"Parser V6 (Spatial + Robust) Complete. Saved to {json_output}")

if __name__ == "__main__":
    main()