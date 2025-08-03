import sys
import fitz

fname = sys.argv[1]

section_keyword = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "COURSEWORK", "LINKS"]


with fitz.open(fname) as doc:

    sections = {}
    current_section = None

    for page in doc:
        page_width = page.rect.width
        midpoint = page_width/2

        text_dict = page.get_text("dict")
        sorted_blocks = sorted(text_dict["blocks"], key=lambda b:(b["bbox"][1], b["bbox"][0]))

        for block in sorted_blocks:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        #getting details
                        if not text:
                            continue
                        span_x0 = span["bbox"][0]
                        font = span["font"]
                        size = span["size"]
                        #checking for left and right
                        if span_x0 < midpoint:
                            column = "left"
                        elif span_x0 >= midpoint:
                            column = "right" 
                        #Now checking for keyword
                        upper_text = text.upper()
                        is_heading = False
                        for keyword in section_keyword:
                            if keyword in upper_text:   #checking via section_keywords using flag
                                current_section = keyword
                                is_heading = True
                                break
                                
                            #checking via font size and style
                        if current_section == None and not is_heading:
                            if ("Bold" in font and size > 12):
                                current_section = "Heading"
                            elif ("Bold" in font and size < 12):
                                current_section = "section heading"
                            elif (not "Bold" in font and size < 12):
                                current_section = "Body"
                        
                        if current_section not in sections:
                                sections[current_section] = []

                        if not is_heading:
                            sections[current_section].append(text) #to append text regardless of section

print("Output\n")
for section, text in sections.items():
    print(f"section: {section}")
    print("\nNOW TEXT\n")
    for t in text:
        print(t)
    print("---"*20)
