import sys
import fitz

fname = sys.argv[1]
section_keyword = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS","COURSEOWRK", "LINKS"]

with fitz.open(fname) as doc:

    current_section = None
    sections = {}
    para_font = {}
    para_size = {}
    unique_font = set()
    unique_size = set()

    for page in doc:
        page_width = page.rect.width
        midpoint = page_width/2
        text_dict = page.get_text("dict")

        sorted_blocks = sorted(text_dict["blocks"], key=lambda b:(b["bbox"][1], b["bbox"][0]))

        for block in sorted_blocks:
            if block["type"] == 0:
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
                        
                    line_y0 = line["bbox"][1] #calculating y0 y1 outside of span
                    line_y1 = line["bbox"][3] 
                    is_heading = False

                    upper_text = line_text.upper()
                    for keyword in section_keyword:
                         if keyword in upper_text:
                              current_section = keyword
                              is_heading = True
                              break
                    
                    if current_section == None and not is_heading:
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

                    if prev_y1 == None:
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





