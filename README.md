# 📄 AI Document Data Extractor

An intelligent Document Data Extractor (Agent) that ingests messy, unstructured receipts and invoices (Images/PDFs) and transforms them into validated, mathematically verified JSON. 

Built with an emphasis on **human-in-the-loop safety**, this agent uses a deterministic Python validation layer to fact-check the LLM's math and flag anomalous fees, ensuring bad data never silently enters your database.

---

## 🚀 The One Job
**This agent takes raw images/PDFs of physical receipts and produces a structured, mathematically validated JSON object containing line items, taxes, discounts, and totals.**

## 🛠️ Architecture & Tech Stack
*   **Frontend UI:** Vanilla HTML/JS/CSS (Offline, side-by-side verification interface).
*   **Backend Server:** FastAPI & Uvicorn.
*   **OCR Engine:** Tesseract OCR (with dynamic cross-platform path resolution) and OpenCV for deskewing/denoising.
*   **LLM Engine:** `llama-3.3-70b-versatile` accessed via the Groq API for lightning-fast parsing.

## ⚙️ Setup & Installation

This project is designed to run seamlessly on Windows, Mac, or Linux. 

### 1. Prerequisites
You must have **Tesseract OCR** installed on your system:
*   **Windows:** Download the installer from the official UB-Mannheim repository.
*   **Mac:** `brew install tesseract`
*   **Linux:** `sudo apt install tesseract-ocr`

### 2. Clone and Install
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
cd YOUR_REPO_NAME

# (Optional) Create a virtual environment
python -m venv venv
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys
Create a file named literally `.env` in the root folder and add your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
```

---

## 🏁 Running the Agent End-to-End

1. Start the local server by running the application script:
```bash
python app.py
```
2. The server will dynamically find an available port and automatically open a browser tab (e.g., `http://localhost:8000`).
3. Upload a receipt or invoice (from the `samples/` folder or your own).
4. View the original document and the extracted, validated JSON side-by-side.

*Extracted JSON files are automatically saved to the `outputs/` directory.*

---

## 🧠 Design Choices & Validation Logic

LLMs are highly capable at semantic extraction but notoriously unreliable at deterministic arithmetic. To solve this, the agent decouples extraction from mathematical validation.

**Validation Logic (`_validation` block):**
The Python backend programmatically verifies the LLM's output using the formula:
`Calculated Total = Sum(Line Items) + Tax - Discount`

The backend checks for equality (within a $0.05 tolerance) against both **Tax-Exclusive** and **Tax-Inclusive** formulas. If the extracted `grand_total` does not match the calculated total, `is_valid` is set to `false`, and a warning is passed to the UI.

---

## ⚠️ Tradeoffs & Known Limitations

Given the 24-hour hackathon constraint, the following design tradeoffs were made:

*   **Unaccounted Fees (Service Charges & Rounding):** The current JSON schema is optimized for standard retail extraction (Items, Tax, Discount). Receipts containing additional complex fees—such as a 10% Restaurant Service Charge or fractional rounding adjustments—will intentionally fail the mathematical sanity check. The formula will detect the missing funds and flag the document with a warning. This is a designed feature to ensure anomalous fee structures are routed to a human for review rather than silently passing bad data into a database.
*   **Implicit Sub-item Pricing:** Fast food receipts often list combo items (e.g., "Medium Fries") beneath a main meal with no printed price. We explicitly prompt the LLM to assign these a `0.0` value rather than hallucinating an estimated cost.
*   **OCR Artefact Noise:** Heavily crumpled receipts or faded ink can occasionally cause Tesseract to read barcodes or phone numbers as monetary values, which will trigger a math validation failure.