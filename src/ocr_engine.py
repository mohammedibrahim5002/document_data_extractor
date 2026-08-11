import os
import sys
import platform
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image


# Dynamic Tesseract Path Setup

def _set_tesseract_path():
    """
    Locates Tesseract executable and verifies the language data exists.
    """
    system = platform.system()
    tess_cmd = shutil.which("tesseract")

    # 1. Find Tesseract Executable
    if system == 'Windows':
        if not tess_cmd:
            candidates = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\miniconda3\Library\bin\tesseract.exe',
                r'C:\miniconda3\envs\ml_finance\Library\bin\tesseract.exe'
            ]
            for c in candidates:
                if os.path.exists(c):
                    tess_cmd = c
                    break
    
    if tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

    # 2. Find TESSDATA_PREFIX (Must contain eng.traineddata)
    if system == 'Windows':
        tessdata_candidates = [
            r'C:\Program Files\Tesseract-OCR\tessdata',
            r'C:\Program Files (x86)\Tesseract-OCR\tessdata',
            r'C:\miniconda3\share\tessdata',
            r'C:\miniconda3\envs\ml_finance\share\tessdata'
        ]
        
        # If we found an exe, check relative to it
        if tess_cmd:
            base_dir = os.path.dirname(tess_cmd)
            tessdata_candidates.insert(0, os.path.join(base_dir, 'tessdata'))
            tessdata_candidates.insert(1, os.path.join(os.path.dirname(base_dir), 'share', 'tessdata'))

        # CRITICAL FIX: Only set the prefix if eng.traineddata actually exists there!
        for td in tessdata_candidates:
            if os.path.exists(os.path.join(td, 'eng.traineddata')):
                os.environ['TESSDATA_PREFIX'] = td
                break

_set_tesseract_path()


# Preprocessing Functions 

def load_image(image_path):
    """
    Load image from disk as a numpy array (BGR).
    Handles image files and single-page PDFs.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f'Image not found: {path}')

    if path.suffix.lower() == '.pdf':
        try:
            import fitz  # PyMuPDF
            doc  = fitz.open(str(path))
            page = doc[0]
            mat  = fitz.Matrix(2.0, 2.0)
            pix  = page.get_pixmap(matrix=mat)
            img  = np.frombuffer(pix.samples, dtype=np.uint8)
            img  = img.reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img
        except ImportError:
            raise ImportError('PDF support requires: pip install pymupdf')
    else:
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f'Could not read image: {path}')
        return img


def preprocess(img):
    """
    Clean up the image so Tesseract reads it accurately.
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    h, w = gray.shape
    if max(h, w) < 1000:
        scale = 1500 / max(h, w)
        gray  = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = _deskew(gray)
    gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10
    )

    return binary


def _deskew(gray):
    """
    Detect tilt angle and rotate image to correct it.
    """
    try:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None or len(lines) == 0:
            return gray

        angles = []
        for line in lines[:20]:
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            if -45 < angle < 45:
                angles.append(angle)

        if not angles:
            return gray

        skew_angle = float(np.median(angles))

        if abs(skew_angle) < 0.3:
            return gray

        h, w   = gray.shape
        center = (w // 2, h // 2)
        M      = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        result = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return result

    except Exception:
        return gray


# Tesseract OCR

def run_tesseract(img, stem=''):
    """
    Run Tesseract on a preprocessed image.
    Returns list of token dicts with bounding boxes and confidence.
    """
    config = '--psm 6 --oem 3'

    data = pytesseract.image_to_data(
        img,
        config=config,
        output_type=pytesseract.Output.DICT
    )

    tokens = []
    n      = len(data['text'])

    for i in range(n):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])

        if not text or conf < 10:
            continue

        x = data['left'][i]
        y = data['top'][i]
        w = data['width'][i]
        h = data['height'][i]

        if w == 0 or h == 0:
            continue

        tokens.append({
            'stem'    : stem,
            'text'    : text,
            'x_min'   : x,
            'y_min'   : y,
            'x_max'   : x + w,
            'y_max'   : y + h,
            'width'   : w,
            'height'  : h,
            'conf'    : conf,
            'line_num': data['line_num'][i],
            'word_num': data['word_num'][i],
        })

    return tokens


def load_box_file(box_path, stem=''):
    """
    Load ground-truth bounding boxes from a SROIE .txt box file.
    """
    path   = Path(box_path)
    tokens = []

    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(',')
            if len(parts) < 9:
                continue

            try:
                coords = list(map(int, parts[:8]))
            except ValueError:
                continue

            text = ','.join(parts[8:]).strip()
            if not text:
                continue

            xs = coords[0::2]
            ys = coords[1::2]

            tokens.append({
                'stem'    : stem,
                'text'    : text,
                'x_min'   : min(xs),
                'y_min'   : min(ys),
                'x_max'   : max(xs),
                'y_max'   : max(ys),
                'width'   : max(xs) - min(xs),
                'height'  : max(ys) - min(ys),
                'conf'    : -1,
                'line_num': 0,
                'word_num': 0,
            })

    return tokens


def normalise_coords(tokens, img_w, img_h):
    """
    Add normalised x/y positions to each token.
    """
    for t in tokens:
        t['x_norm']        = round(t['x_min'] / img_w, 4) if img_w else 0
        t['y_norm']        = round(t['y_min'] / img_h, 4) if img_h else 0
        t['x_center_norm'] = round((t['x_min'] + t['x_max']) / 2 / img_w, 4) if img_w else 0
        t['y_center_norm'] = round((t['y_min'] + t['y_max']) / 2 / img_h, 4) if img_h else 0
        t['width_norm']    = round(t['width']  / img_w, 4) if img_w else 0
        t['height_norm']   = round(t['height'] / img_h, 4) if img_h else 0
    return tokens


# Extraction Entry Points 

def extract_tokens(image_path, box_path=None):
    """
    Main extraction logic. Returns token dictionaries.
    """
    image_path = Path(image_path)
    stem       = image_path.stem

    img          = load_image(image_path)
    img_h, img_w = img.shape[:2]

    if box_path is not None:
        tokens = load_box_file(box_path, stem=stem)
    else:
        processed = preprocess(img)
        tokens    = run_tesseract(processed, stem=stem)

    tokens = normalise_coords(tokens, img_w, img_h)

    return tokens


def perform_ocr(file_path: str) -> str:
    """
    Bridge function for the LLM Agent.
    Runs token extraction and joins the tokens into a single text string.

    Plain .txt files skip OCR entirely -- the file content IS the text,
    so there's nothing to extract from an image.
    """
    if Path(file_path).suffix.lower() == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    tokens = extract_tokens(file_path)
    raw_text = " ".join([t['text'] for t in tokens])
    return raw_text