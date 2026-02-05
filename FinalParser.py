import sys
import fitz
import json
import os
import re

DEBUG = False

FULL_WIDTH_RATIO = 0.6
HEADER_ABOVE_TOL = 2

SECTION_KEYWORDS = [
    "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE", "SKILLS",
    "PROJECTS", "LINKS", "SUMMARY", "CERTIFICATIONS",
    "EXPERTISE", "ABOUT ME", "CONTACT", "REFERENCE", "REFERENCES",
    "PROFILE", "LANGUAGE", "LANGUAGES", "HISTORY"
]

DATE_PATTERN_RAW = r'''(?ix)
(
    (?:\b(?:19|20)\d{2}\b(?:\s*[-–—]\s*(?:19|20)\d{2}\b)?) |
    (?:\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b
        (?:\s*(?:to|-|–|—)\s*
        (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4})?
    ) |
    \b(?:Present|Current|Now|NOW)(?:\s*[-–—]\s*\d{4})?\b
)
'''
DATE_RE = re.compile(DATE_PATTERN_RAW)
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
LINK_RE = re.compile(r'(https?://[^\s]+|www\.[^\s]+)')

def clean_text(text):
    if not text: return ""
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    text = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219]', '', text)
    return text.strip()

def calculate_overlap_ratio(min1, max1, min2, max2):
    overlap = max(0, min(max1, max2) - max(min1, min2))
    min_width = min(max1 - min1, max2 - min2)
    
    if min_width < 10: 
        return 0
        
    return overlap / min_width

def dedupe_keep_order(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def extract_name_by_font(doc):
    page = doc[0]
    text_dict = page.get_text("dict")
    max_size = 0
    name = "Unknown"
    
    ignore_headers = {"RESUME", "CV", "CURRICULUM", "CURRICULUM VITAE", "CURRICULUM-VITAE"}

    for block in text_dict["blocks"]:
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    t = span["text"].strip()
                    t_upper = t.upper()
                    
                    if len(t.split()) > 4 or t.isdigit() or "@" in t or not t:
                        continue
                    
                    if t_upper in ignore_headers:
                        continue

                    if span["size"] > max_size:
                        max_size = span["size"]
                        name = t
                    elif span["size"] == max_size:
                        if name.isupper() and any(c.islower() for c in t):
                            name = t
    return name

def extract_entities(text):
    entities = {"email": None, "phone": None, "links": []}

    m_email = EMAIL_RE.search(text)
    if m_email:
        entities["email"] = m_email.group(0)

    m_phone = PHONE_RE.search(text)
    if m_phone:
        raw_phone = m_phone.group(0)
        entities["phone"] = re.sub(r'[^\d+]', '', raw_phone)

    links = LINK_RE.findall(text)
    entities["links"] = dedupe_keep_order(links)

    return entities

def structure_experience_section(lines):
    jobs = []
    buffer = []
    current = None

    for line in lines:
        text = line.strip()
        if not text: continue

        is_date = bool(DATE_RE.search(text))
        
        if "Representative" in text: is_date = False

        if is_date:
            header_parts = []
            while buffer and len(header_parts) < 3:
                cand = buffer.pop()
                if len(cand.split()) <= 8 and not cand.endswith('.'):
                    header_parts.insert(0, cand)
                else:
                    buffer.append(cand)
                    break

            if current:
                current["details"].extend(buffer)
                jobs.append(current)

            header = " | ".join(header_parts + [text]) if header_parts else text
            current = {"header": header, "details": []}
            buffer = []
        else:
            buffer.append(text)

    if current:
        current["details"].extend(buffer)
        jobs.append(current)
    elif buffer:
        jobs.append({"header": "Content", "details": buffer})

    for j in jobs:
        j["details"] = dedupe_keep_order(j["details"])

    return jobs

def main():
    if len(sys.argv) < 2:
        print("Usage: python FinalParser.py <resume.pdf>")
        sys.exit(1)

    fname = sys.argv[1]

    final_data = {
        "metadata": {"filename": fname, "name": ""},
        "entities": {},
        "sections": {}
    }

    all_lines = []
    headers = []

    with fitz.open(fname) as doc:
        final_data["metadata"]["name"] = extract_name_by_font(doc)

        for page_idx, page in enumerate(doc):
            page_width = page.rect.width
            text_dict = page.get_text("dict")

            for block in text_dict["blocks"]:
                if block["type"] != 0: continue

                for line in block["lines"]:
                    x0, y0, x1, y1 = line["bbox"]
                    spans = line["spans"]

                    current_txt = ""
                    seg_x0 = x0
                    gap_threshold = max(12, page_width * 0.01)

                    for i, span in enumerate(spans):
                        txt = span["text"]
                        if not txt.strip(): continue

                        if i > 0:
                            prev = spans[i - 1]
                            gap = span["bbox"][0] - prev["bbox"][2]
                            if gap > gap_threshold:
                                clean = clean_text(current_txt)
                                if clean:
                                    upper = clean.upper()
                                    kw = next((k for k in SECTION_KEYWORDS if upper == k or upper.startswith(k + " ")), None)
                                    
                                    obj = {
                                        "text": clean,
                                        "bbox": (seg_x0, y0, prev["bbox"][2], y1),
                                        "page": page_idx,
                                        "page_width": page_width,
                                        "is_header": bool(kw),
                                        "keyword": kw
                                    }
                                    all_lines.append(obj)
                                    if kw: headers.append(obj)

                                current_txt = ""
                                seg_x0 = span["bbox"][0]

                        current_txt += txt

                    clean = clean_text(current_txt)
                    if clean:
                        upper = clean.upper()
                        kw = next((k for k in SECTION_KEYWORDS if upper == k or upper.startswith(k + " ")), None)

                        obj = {
                            "text": clean,
                            "bbox": (seg_x0, y0, x1, y1),
                            "page": page_idx,
                            "page_width": page_width,
                            "is_header": bool(kw),
                            "keyword": kw
                        }
                        all_lines.append(obj)
                        if kw: headers.append(obj)

    all_lines.sort(key=lambda x: (x["page"], x["bbox"][1]))

    if DEBUG:
        print("\n--- DEBUG: HEADERS DETECTED ---")
        for h in headers:
            print(f"Page {h['page']} | {h['keyword']} | {h['text']}")
        print("\n--- DEBUG: FIRST 20 LINES ---")
        for l in all_lines[:20]:
            print(f"Page {l['page']} | {l['text'][:30]}...")

    sections_raw = {}

    for line in all_lines:
        if line["is_header"]: continue

        best_header = None
        min_vertical_dist = float("inf")
        
        line_x0, line_y0, line_x1, _ = line["bbox"]

        for h in headers:
            if h["page"] != line["page"]: continue
            
            h_y1 = h["bbox"][3]
            if h_y1 > line_y0 + HEADER_ABOVE_TOL: continue

            h_x0, _, h_x1, _ = h["bbox"]
            header_width = h_x1 - h_x0
            
            overlap_ratio = calculate_overlap_ratio(line_x0, line_x1, h_x0, h_x1)
            
            is_aligned = False
            page_w = h.get("page_width", 800)
            if header_width > (page_w * FULL_WIDTH_RATIO): 
                is_aligned = True
            elif overlap_ratio > 0.4: 
                is_aligned = True
            
            if is_aligned:
                dist = line_y0 - h_y1
                if dist < min_vertical_dist:
                    min_vertical_dist = dist
                    best_header = h["keyword"]

        sec = best_header if best_header else "UNLABELED"
        sections_raw.setdefault(sec, []).append(line["text"])

    for sec in ["EXPERIENCE", "WORK EXPERIENCE", "EDUCATION", "HISTORY"]:
        if sec in sections_raw:
            final_data["sections"][sec] = structure_experience_section(sections_raw[sec])

    for sec, lines in sections_raw.items():
        if sec not in final_data["sections"]:
            final_data["sections"][sec] = dedupe_keep_order(lines)

    full_text_content = " ".join([l["text"] for l in all_lines])
    final_data["entities"] = extract_entities(full_text_content)

    out_name = os.path.splitext(os.path.basename(fname))[0] + "_final_parsed.json"
    with open(out_name, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print(f"Parser Final Complete. Output: {out_name}")

if __name__ == "__main__":
    main()