import sys
import fitz
import re
import json
import os

def clean_text(text):
    text = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219]', '', text)
    return " ".join(text.split())

def extract_entities(text_content):
    entities = {
        "email": None,
        "phone": None,
        "links": []
    }
    
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_pattern, text_content)
    if email_match:
        entities["email"] = email_match.group(0)

    phone_pattern = r'\(?\+?[0-9]{1,3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
    phone_match = re.search(phone_pattern, text_content)
    if phone_match:
        entities["phone"] = phone_match.group(0)

    url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
    links = re.findall(url_pattern, text_content)
    entities["links"] = links

    return entities

def parse_resume(fname):
    section_keyword = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "COURSEWORK", "LINKS", "CERTIFICATIONS", "SUMMARY"]
    
    with fitz.open(fname) as doc:
        current_section = "CONTACT_INFO"
        sections = {current_section: []}
        

        para_font = {}
        para_size = {}

        for page in doc:
            text_dict = page.get_text("dict")
            
            blocks = text_dict["blocks"]

            for block in blocks:
                if block["type"] == 0:
                    paragraph_lines = []
                    
                    for line in block["lines"]:
                        line_text = ""
                        max_size = 0
                        span_font = ""
                        

                        for span in line["spans"]:
                            line_text += span["text"]
                            size = span["size"]
                            if max_size < size:
                                max_size = size
                                span_font = span["font"]
                        

                        if span_font not in para_font: para_font[span_font] = 0
                        para_font[span_font] += 1
                        

                        clean_line = line_text.strip()
                        upper_text = clean_line.upper()
                        is_new_section = False
                        

                        
                        for keyword in section_keyword:
                            if keyword == upper_text:
                                current_section = keyword
                                is_new_section = True
                                break
                            elif keyword in upper_text and len(clean_line.split()) < 5:
                                current_section = keyword
                                is_new_section = True
                                break
                        
                        
                        if not is_new_section:
                            if "Bold" in span_font and max_size > 14:
                                pass

                        if is_new_section:
                            if current_section not in sections:
                                sections[current_section] = []
                        else:
                            if clean_line:
                                paragraph_lines.append(clean_line)
                    if paragraph_lines:
                        full_paragraph = " ".join(paragraph_lines)
                        cleaned_paragraph = clean_text(full_paragraph)
                        sections[current_section].append(cleaned_paragraph)

    return sections

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python Example.py <path_to_resume.pdf>")
        sys.exit(1)

    fname = sys.argv[1]
    parsed_sections = parse_resume(fname)

    contact_text = " ".join(parsed_sections.get("CONTACT_INFO", []))
    if not contact_text and "Body" in parsed_sections:
        contact_text = " ".join(parsed_sections["Body"][:5])
        
    entities = extract_entities(contact_text)
    final_output = {
        "entities": entities,
        "sections": parsed_sections
    }

    base_name = os.path.splitext(os.path.basename(fname))[0]
    output_path = f"{base_name}_extracted.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    print(f"Successfully parsed: {output_path}")