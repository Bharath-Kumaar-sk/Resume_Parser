import sys
import fitz

fname = sys.argv[1]

with fitz.open(fname) as doc:
    
    for page in doc:
        page_width = page.rect.width
        midpoint = page_width/2

        text_dict = page.get_text("dict")
        sorted_block = sorted(text_dict["blocks"], key=lambda b:(b["bbox"][1], b["bbox"][0]))

        for block in sorted_block: #inside block
            if block["type"] == 0: #text
                x0, y0, x1, y1 = block["bbox"][0], block["bbox"][1], block["bbox"][2], block["bbox"][3]
                #next step --> sort left - right using the span instead of block
                for line in block["lines"]: #inside line
                    for span in line["spans"]: #inside span
                        text = span["text"]
                        if text:
                            size = span["size"]
                            font = span["font"]
                            if x0 < midpoint:
                                print(f"left column -- {x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}")
                                print(f"size = {size} font = {font}")
                                print("\ntext: "+text)
                            elif x0 >= midpoint:
                                print(f"right column -- {x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}")
                                print(f"size = {size} font = {font}")
                                print("\ntext: "+text)

