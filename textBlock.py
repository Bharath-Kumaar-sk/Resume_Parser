import sys
import fitz

fname = sys.argv[1]

section_keyword = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "COURSEWORK", "LINKS"]


with fitz.open(fname) as doc:

    sections = {}
    font_dict= {}
    size_dict = {}
    current_font = None
    current_section = None
    current_size = None

    for page in doc:
        page_width = page.rect.width
        midpoint = page_width/2

        text_dict = page.get_text("dict")
        sorted_blocks = sorted(text_dict["blocks"], key=lambda b:(b["bbox"][1], b["bbox"][0]))

        for block in sorted_blocks:
            if block["type"] == 0: #0 means Text
                for line in block["lines"]:
                    line_text = ""
                    max_size = 0
                    span_font = ""

                    for span in line["spans"]:
                        #getting details
                        line_text += span["text"] #building line text
                        size = span["size"]
                        if max_size < size: #max size in each line
                             max_size = size
                    
                    #Now a full line is created
                    span_x0 = span["bbox"][0] #to check left column and right column
                    for Chksize in line_text:
                          if max_size == line_text["size"]:
                                span_font = line_text["font"] #to get the font of largest size
                    #checking for left and right
                    if span_x0 < midpoint:
                        column = "left"
                    elif span_x0 >= midpoint:
                        column = "right" 
                        #Now checking for keyword
                    
                    upper_text = line_text.upper()
                    is_heading = False
                    for keyword in section_keyword:
                        if keyword in upper_text:   #checking via section_keywords using flag
                                current_section = keyword
                                current_font = span_font
                                current_size = max_size
                                is_heading = True
                                break
                                
                            #checking via font size and style
                    if current_section == None and not is_heading:
                        if ("Bold" in span_font and size > 12):
                                current_section = "Heading"
                        elif ("Bold" in span_font and size < 12):
                                current_section = "section heading"
                        elif (not "Bold" in span_font and size < 12):
                                current_section = "Body"
                        
                    if current_section not in sections:
                                sections[current_section] = []
                                font_dict[current_font] = []
                                size_dict[current_size] = []

                    if not is_heading:
                            sections[current_section].append(line_text) #to append text regardless of section
                            font_dict[current_font].append(span_font)
                            size_dict[current_size].append(max_size)

print("Output\n")
for section, text in sections.items():
    print(f"section: {section}")
    print("\nNOW TEXT\n")
    for t in text:
        print(t)
    print("---"*20)
