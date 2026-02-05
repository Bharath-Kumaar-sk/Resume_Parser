Below is the **final, paste-ready `README.md`**.
You can copy this **as-is** into your repository root.

---

````markdown
# Resume Parser — Rule-Based PDF Extractor (parser_v12)

A deterministic, rule-based resume parser that extracts structured information from PDF resumes using spatial layout analysis, lexical cues, and robust date heuristics.

This project focuses on **explainability, robustness, and reproducibility** rather than machine-learning black boxes. It is designed to handle common real-world resume layouts, including single-column, two-column, and timeline-style designs.

---

## Project Overview

The parser processes PDF resumes and produces structured JSON output containing:

- Candidate name (best-effort)
- Contact entities (email, phone, links)
- Sectioned resume content
- Structured experience entries (header + bullet details)

The implementation uses **PyMuPDF (fitz)** to access precise text coordinates and applies rule-based heuristics to infer document structure.

---

## Key Features

- Rule-based, deterministic parsing (no ML required)
- Robust section header detection using lexical + spatial cues
- Adaptive multi-column handling via span gap analysis
- Date range detection (years, month-year, `Present`, `NOW-YYYY`)
- Experience grouping using date anchors and bounded look-back
- Full-document entity extraction (email, phone, URLs)
- Configurable debug mode for inspection and tuning
- Clean, normalized JSON output suitable for downstream systems

---

## Supported Resume Layouts

- Single-column text resumes  
- Two-column professional resumes  
- Chronological experience layouts  
- Timeline-style resumes (partial support via heuristics)

---

## Installation

### Requirements
- Python 3.9+
- PyMuPDF

### Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell

pip install --upgrade pip
pip install pymupdf
````

Optional `requirements.txt`:

```
pymupdf>=1.22.0
```

---

## Usage

Run the parser from the command line:

```bash
python FinalParser.py <resume.pdf>
```

Example:

```bash
python FinalParser.py samples/Sample3.pdf
```

Output:

```
Sample3_final_parsed.json
```

---

## Output Format

The parser outputs a structured JSON file with the following schema:

```json
{
  "metadata": {
    "filename": "Sample3.pdf",
    "name": "Candidate Name"
  },
  "entities": {
    "email": "email@example.com",
    "phone": "1234567890",
    "links": ["www.example.com"]
  },
  "sections": {
    "EXPERIENCE": [
      {
        "header": "Role | Company | Date Range",
        "details": [
          "Bullet point 1",
          "Bullet point 2"
        ]
      }
    ],
    "EDUCATION": [...],
    "SKILLS": [...],
    "CONTACT": [...],
    "UNLABELED": [...]
  }
}
```

### Notes

* Phone numbers are normalized (digits only, leading `+` preserved).
* Experience entries are grouped using detected date anchors.
* `UNLABELED` contains text that could not be confidently assigned.

---

## Algorithm Summary

1. **PDF Text Extraction**

   * Extract span-level text with bounding boxes using PyMuPDF.

2. **Line Segmentation**

   * Merge spans into line segments.
   * Split segments using an adaptive gap threshold based on page width.

3. **Header Detection**

   * Detect section headers using keyword matching.
   * Tag headers at creation time to avoid later ambiguity.

4. **Section Assignment**

   * Assign lines to the nearest valid header above them using:

     * Vertical distance
     * Horizontal overlap ratio
     * Page-relative full-width detection

5. **Experience Structuring**

   * Detect date anchors using precompiled regex.
   * Group job entries using bounded look-back heuristics.
   * Deduplicate bullet points.

6. **Entity Extraction**

   * Extract email, phone, and links from the full document text.

---

## Configuration & Tuning

Key constants are defined at the top of `parser_v12.py`:

* `DEBUG` — enable detailed parsing logs
* `FULL_WIDTH_RATIO` — header width threshold (default: `0.6`)
* `HEADER_ABOVE_TOL` — vertical tolerance in pixels (default: `2`)

These values can be tuned for different resume styles.

---

## Evaluation Strategy

Recommended evaluation approach:

1. Create a `samples/` directory with diverse resumes:

   * Simple one-column
   * Two-column professional
   * Timeline-style
   * Academic CV
   * Minimalist / modern design

2. For each sample, record:

   * Sections detected
   * Experience entries found
   * Percentage of `UNLABELED` content
   * Entity extraction success

3. Document observations rather than forcing perfect accuracy.

---

## Known Limitations

* Timeline-style resumes with visually detached date markers may require additional heuristics.
* Phone number regex is primarily US-centric.
* Headers are matched only within the same page by default.
* Scanned PDFs (image-only) require OCR preprocessing.
* Experience headers are stored as combined strings (no semantic field splitting).

These limitations are documented design trade-offs, not bugs.

---

## Project Status

**Stable — feature complete**

This version (`Final_Parser`) represents a stable, documented release suitable for:

* Academic submission
* Portfolio projects
* Downstream experimentation (ATS, analytics, ML pipelines)

Further work would be considered **enhancements**, not required fixes.

---

## Possible Enhancements

* Resume layout classifier (standard vs timeline)
* Experience field normalization (title, company, start/end dates)
* Confidence scores per section/job
* OCR integration for scanned resumes
* REST API or batch processing wrapper

---

---

## Attribution

Built using PyMuPDF (fitz):
[https://pymupdf.readthedocs.io/](https://pymupdf.readthedocs.io/)

**End of README**

