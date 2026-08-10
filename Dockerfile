FROM python:3.12-slim

# Tesseract OCR is a system-level dependency (not a pip package) -- this is
# the one thing that differs across Windows/Mac/Linux natively, so baking
# it into the image removes that entire class of setup problem.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first so Docker caches this layer -- rebuilds after a
# code change won't re-download every package, only after requirements.txt
# actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
