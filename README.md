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

### Option A: Docker (recommended)

This avoids every OS-specific setup issue below entirely — Tesseract install
differences, Python environment conflicts, PATH problems. All you need is
Docker installed.

```bash
git clone https://github.com/mohammedibrahim5002/document_data_extractor
cd document_data_extractor

echo "GROQ_API_KEY=your_groq_api_key_here" > .env
# (or copy .env.example to .env and edit it)

docker build -t doc-extractor .
docker run -p 8000:8000 --env-file .env doc-extractor
```

Open `http://localhost:8000`.

### Option B: Local Python environment

Unlike Option A, this depends on your local Python/Tesseract setup being clean.

#### Prerequisites

Tesseract OCR must be installed on your system:

* **Windows:** Download and run the installer from the official Tesseract repository.
* **macOS:** `brew install tesseract`
* **Linux:** `sudo apt install tesseract-ocr`

#### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/mohammedibrahim5002/document_data_extractor
   cd document_data_extractor
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

   Activate it — **use the command matching your shell**:
   * Command Prompt (Windows): `venv\Scripts\activate.bat`
   * PowerShell (Windows): `.\venv\Scripts\Activate.ps1` — if this errors about
     script execution being disabled, run
     `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry.
   * macOS/Linux: `source venv/bin/activate`

   Your prompt should now show `(venv)`. If you also have Anaconda/Miniconda
   installed, run `conda deactivate` first if your prompt shows `(base)` —
   installing into a conda base environment is a common source of Windows
   permission errors with this project's dependencies.

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