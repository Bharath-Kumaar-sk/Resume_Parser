import sys, pathlib
import fitz

fname = sys.argv[1]

with fitz.open(fname) as doc:

    for page in doc:
        Findblocks = page.get_text("blocks")
        text_dict = page.get_text("dict")

        left_column = []
        right_column = []

        page_width = page.rect.width
        midpoint = page_width/2

        sorted_blocks = sorted(Findblocks, key=lambda b: (b[1], b[0])) #sorting the block based on b[1] - y0 (top)
        #b[1] and b[0] works because OUT PUT OF FindBlocks is a tuple     and b[0] - x[0] - left
        for block in text_dict["blocks"]: #provides spans - basically lines with same font, size - or simply a line - section headers, heading
            if block["type"] == 0: 
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        size = span["size"]
                        font = span["font"]
                        print(f"Text: {text}")
                        print(f"Font: {font}, Size: {size}")
                        print("-" * 30)
        
        for b in sorted_blocks: #provides block - grouped together - paragrpahs, section headers, heading
            text = b[4].strip()
            if text:
                x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
                if x0 < midpoint:
                    print("Block is left column")
                    print(f"coordinates: {x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}")
                    print(text)
                    print("-"*30)
                if x0 > midpoint:
                    print("Block is right column")
                    print(f"coordinates: {x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}")
                    print(text)
                    print("-"*30)


    #Use spans to get the text, font details on sorting at the same time