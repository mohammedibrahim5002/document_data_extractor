import os
import shutil
import json
import socket
import threading
import webbrowser
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import uvicorn
from dotenv import load_dotenv

# Load environment variables (.env)
load_dotenv()

from src.ocr_engine import perform_ocr
from src.parser import process_document

app = FastAPI(title="Document Extractor API")

# Serve the Offline HTML UI
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    if not os.path.exists("index.html"):
        return "<h1>Error: index.html not found in root directory.</h1>"
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# Extraction API Endpoint
from fastapi import HTTPException

@app.post("/api/extract")
async def extract_data(file: UploadFile = File(...)):
    # 1. Validate the file type
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only JPEG, PNG, and PDF are supported."
        )
        
    try:
        # Step A: Ingestion (OCR)
        raw_text = perform_ocr(temp_file_path)
        
        # Step B: LLM Processing & Sanity Checks
        validated_json = process_document(raw_text)
        
        # Step C: Save to outputs/ folder
        os.makedirs("outputs", exist_ok=True)
        output_filename = file.filename.rsplit('.', 1)[0] + "_result.json"
        with open(os.path.join("outputs", output_filename), "w", encoding="utf-8") as f:
            json.dump(validated_json, f, indent=4)
            
        return validated_json
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def find_free_port(start_port=8000):
    """Finds an available network port starting from start_port."""
    port = start_port
    while port < 8100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
        port += 1
    return start_port

def open_browser(port):
    """Opens default system browser once server is running."""
    webbrowser.open(f"http://localhost:{port}")

if __name__ == "__main__":
    port = find_free_port(8000)
    print("Starting local offline web server...")
    print(f"Running on: http://localhost:{port}")
    
    # Automatically open browser
    threading.Timer(1.5, open_browser, args=[port]).start()
    
    uvicorn.run(app, host="0.0.0.0", port=port)