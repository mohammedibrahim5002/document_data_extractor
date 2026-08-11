import os
import shutil
import json
import socket
import threading
import webbrowser
import traceback  # Added for detailed error logging
from fastapi import FastAPI, UploadFile, File, HTTPException
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
@app.post("/api/extract")
async def extract_data(file: UploadFile = File(...)):
    # 1. Validate the file type
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only JPEG, PNG, and PDF are supported."
        )
    
    # Initialize the variable as None so the 'finally' block doesn't crash if it fails early
    temp_file_path = None 

    try:
        # 2. Define the path and save the uploaded file to disk
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Perform OCR
        raw_text = perform_ocr(temp_file_path)
        
        # 4. Pass the raw text to the LLM and return the JSON
        json_result = process_document(raw_text)
        return json_result

    except Exception as e:
        print("====== ACTUAL ERROR DETAILS ======")
        traceback.print_exc()  # This prints the exact red error to your terminal
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 5. Clean up: Delete the temporary file after processing is done
        if temp_file_path and os.path.exists(temp_file_path):
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