# Document Data Extractor

A web application that extracts structured JSON data from receipt and invoice images or PDFs, featuring automated mathematical validation.

---

## Overview

This application processes receipt and invoice documents using OCR and an LLM to extract itemized descriptions, unit prices, line totals, taxes, and grand totals. Extracted values are passed through a deterministic Python validation module to check mathematical consistency before returning the final JSON.

---

## Tech Stack

* **Frontend:** Vanilla HTML, CSS, JavaScript (Local web UI)
* **Backend:** FastAPI, Uvicorn
* **OCR Engine:** Tesseract OCR, OpenCV
* **Parsing Engine:** Groq API (`llama-3.3-70b-versatile`)

---

## Setup and Installation

### Prerequisites

Tesseract OCR must be installed on your system:

* **Windows:** Download and run the installer from the official Tesseract repository.
* **macOS:** `brew install tesseract`
* **Linux:** `sudo apt install tesseract-ocr`

### Installation Steps

1. Clone the repository:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
   cd YOUR_REPO_NAME
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory and add your API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

## Usage

1. Start the FastAPI server:
   ```bash
   python app.py
   ```

2. Open the web interface in your browser (default: `http://localhost:8000`).
3. Upload a receipt or invoice (JPEG, PNG, or PDF).
4. View the original document preview and extracted JSON output side-by-side.

Processed output files are stored in the `outputs/` directory.

---

## Validation Logic

Extracted numerical values undergo programmatic verification in Python:

$$\text{Calculated Total} = \sum \text{Line Item Totals} + \text{Tax} - \text{Discount}$$

* The module compares the calculated total against the extracted grand total within a $0.05 tolerance.
* Verification supports both tax-inclusive and tax-exclusive document layouts.
* If a discrepancy is found, the `_validation` block in the JSON output marks `is_valid: false` and lists the specific warning.

---

## Known Limitations

* **Unaccounted Fees:** The current schema targets line items, taxes, and discounts. Receipts containing service charges or rounding adjustments will trigger a validation warning for manual review.
* **Unpriced Sub-items:** Combo options or sub-items printed without explicit individual prices are assigned a value of `0.0`.
* **OCR Quality:** Highly degraded or blurry scans may result in misread characters, triggering validation checks.