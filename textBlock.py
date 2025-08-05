import sys
import fitz

fname = sys.argv[1]

section_keyword = ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "COURSEWORK", "LINKS"]


with fitz.open(fname) as doc:

    sections = {}
    font_dict= {}
    size_dict = {}
    unique_font = set()
    unique_size = set()
    current_section = None

    for page in doc:
        page_width = page.rect.width
        midpoint = page_width/2

        text_dict = page.get_text("dict")
        sorted_blocks = sorted(text_dict["blocks"], key=lambda b:(b["bbox"][1], b["bbox"][0]))

        for block in sorted_blocks:
            print("")