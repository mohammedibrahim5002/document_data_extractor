import json
import os
from datetime import datetime
from groq import Groq
from pydantic import BaseModel, Field, ValidationError
from typing import List

# 1. Pydantic Schema for Strict Extraction
class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float

class InvoiceData(BaseModel):
    invoice_id: str = Field(description="The unique identifier for the document. 'UNKNOWN' if not found.")
    date: str = Field(description="Date of the transaction in YYYY-MM-DD format. 'UNKNOWN' if not found.")
    line_items: List[LineItem]
    tax: float = Field(description="Total tax amount. 0.0 if none.", default=0.0)
    discount: float = Field(description="Total discount amount. 0.0 if none.", default=0.0)
    grand_total: float

# Initialize Groq Client (Requires GROQ_API_KEY environment variable)
client = Groq()

def parse_document_with_llm(ocr_text: str) -> dict:
    """Uses Groq and Llama 3 to extract structured data from raw OCR text."""
    system_prompt = """
    You are a precision data extraction agent. 
    Extract the following fields from the messy OCR text into a JSON object:
    - invoice_id (string)
    - date (string, YYYY-MM-DD format)
    - line_items (list of objects with description, quantity, unit_price, total)
    - tax (float, default 0.0)
    - discount (float, default 0.0)
    - grand_total (float)

    CRITICAL EXTRACTION RULES:
    1. If an item or sub-item does NOT have an explicit price, set its unit_price = 0.0 and total = 0.0.
    2. NEVER guess or invent prices. ALL numerical fields MUST be raw floating-point numbers.
    3. DO NOT extract "Subtotal", "Tax", "Rounding", or "Total" as objects in the line_items array. 
    4. If a receipt has multiple columns (like Unit Price, Discount, Amount), the line item's 'total' MUST be the final discounted 'Amount' column.
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", # Free, highly capable open-source model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract data from this text:\n\n{ocr_text}"}
        ],
        temperature=0.0, # Zero creativity, strict extraction
        response_format={"type": "json_object"} # Forces the model to output strict JSON
    )
    
    return json.loads(response.choices[0].message.content)

def run_sanity_checks(data: dict) -> dict:
    warnings = []
    
    # 1. Date Check
    try:
        if data.get("date") and data.get("date") != "UNKNOWN":
            datetime.strptime(data.get("date", ""), "%Y-%m-%d")
    except ValueError:
        warnings.append(f"Invalid date format: {data.get('date')}. Expected YYYY-MM-DD.")
        
    # 2. Math Validation
    items_sum = 0.0
    for item in data.get("line_items", []):
        qty = item.get("quantity", 1.0)
        price = item.get("unit_price", 0.0)
        items_sum += item.get("total", qty * price)
        
    tax = data.get("tax", 0.0)
    discount = data.get("discount", 0.0)
    grand_total = data.get("grand_total", 0.0)
    
    # Check both Tax-Exclusive (Items + Tax - Discount) AND Tax-Inclusive (Items - Discount)
    total_tax_exclusive = items_sum + tax - discount
    total_tax_inclusive = items_sum - discount
    
    is_valid_exclusive = abs(total_tax_exclusive - grand_total) <= 0.05
    is_valid_inclusive = abs(total_tax_inclusive - grand_total) <= 0.05
    
    if not (is_valid_exclusive or is_valid_inclusive):
        warnings.append(
            f"Math Error: Items sum ({items_sum:.2f}) does not match Grand Total ({grand_total:.2f})."
        )
        
    data["_validation"] = {
        "is_valid": len(warnings) == 0,
        "warnings": warnings
    }
    
    return data

def process_document(ocr_text: str) -> dict:
    """Main pipeline function."""
    extracted_json = parse_document_with_llm(ocr_text)

    # Structural validation: does the LLM output actually match the
    # expected shape (types, required fields), independent of the
    # arithmetic checks below.
    try:
        InvoiceData(**extracted_json)
        schema_error = None
    except ValidationError as e:
        schema_error = str(e)

    validated_json = run_sanity_checks(extracted_json)
    if schema_error:
        validated_json["_validation"]["is_valid"] = False
        validated_json["_validation"]["warnings"].append(
            f"Schema validation failed: {schema_error}"
        )
    return validated_json