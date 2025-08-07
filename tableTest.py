import pdfplumber
import sys

fname = sys.argv[1]

with pdfplumber.open(fname) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
        print(f"\n--- Page {page_num} ---")
        tables = page.extract_tables()
        for table_num, table in enumerate(tables, start=1):
            print(f"\nTable {table_num}:")
            for row in table:
                print(row)
