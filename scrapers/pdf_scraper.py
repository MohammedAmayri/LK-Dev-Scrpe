from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import logging
import requests
from bs4 import BeautifulSoup
import os
import re
import cv2
import numpy as np
from PyPDF2 import PdfReader
from io import BytesIO

# Configure logging
logger = logging.getLogger(__name__)

# Set the path to the Tesseract executable (adjust the path as needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\mohammed.amayri\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

# Temporarily add Poppler path to the environment variable
poppler_path = r'C:\poppler-24.08.0\Library\bin'
os.environ['PATH'] += os.pathsep + poppler_path

def scrape_pdf(main_url, solution=None):
    pdf_links = find_pdf_links(main_url)
    if not pdf_links:
        logger.info("No PDF links found on the page.")
        return None

    for pdf_url in pdf_links:
        logger.info(f"Processing potential PDF link: {pdf_url}")
        # Check if the PDF is relevant based on the filename
        if not is_relevant_pdf(pdf_url):
            logger.info(f"Skipping PDF at {pdf_url} because it does not contain relevant keywords in the filename.")
            continue

        if solution == '1':
            logger.info("Using Solution 1")
            extracted_text = process_pdf_with_solution1(pdf_url)
        elif solution == '2':
            logger.info("Using Solution 2")
            extracted_text = process_pdf_with_solution2(pdf_url)
        elif solution == '3':
            logger.info("Using Solution 3")
            extracted_text = process_pdf_with_solution3(pdf_url)
        else:
            logger.info("No specific solution provided. Attempting automatic detection.")
            extracted_text = process_pdf_auto(pdf_url)

        if extracted_text:
            logger.info(f"Relevant text found in PDF: {pdf_url}")
            return extracted_text

    logger.info("No relevant PDF found containing the specified keywords.")
    return None

# Common functions used by all solutions
def pdf_to_images(pdf_content):
    try:
        # Convert PDF to images (multi-page support)
        images = convert_from_bytes(pdf_content, poppler_path=poppler_path)
        return images
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return None

def extract_text_from_image(image):
    try:
        # Extract text using Tesseract
        custom_oem_psm_config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(image, lang='swe', config=custom_oem_psm_config)
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from image: {e}")
        return None

def find_pdf_links(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all potential PDF links
        pdf_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf') or 'pdf' in href.lower():
                pdf_links.append(requests.compat.urljoin(url, href))

        return pdf_links
    except Exception as e:
        logger.error(f"Error finding PDF links: {e}")
        return []

def extract_week_number(text):
    """
    Extracts the week number from the given text.

    Possible patterns:
    - Vecka x
    - Week x
    - V x
    - V. x
    - W x
    """
    week_patterns = [
        r'vecka\s*\d{1,2}',    # Matches 'Vecka 46' or 'Vecka46'
        r'week\s*\d{1,2}',     # Matches 'Week 46' or 'Week46'
        r'\bv\.?\s*\d{1,2}\b', # Matches 'V46', 'V 46', 'V.46', 'V. 46'
        r'\bw\.?\s*\d{1,2}\b', # Matches 'W46', 'W 46', 'W.46', 'W. 46'
    ]

    for pattern in week_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            week_str = match.group()
            # Clean up the string (e.g., remove extra spaces)
            week_str = re.sub(r'\s+', ' ', week_str.strip())
            return week_str.capitalize()
    return None

def extract_week_number_from_url(url):
    """
    Extracts the week number from the URL or filename.
    """
    filename = url.split('/')[-1].lower()

    # Define patterns that match 'vecka' or 'v' at the start or after a separator
    week_patterns = [
        r'(?:^|[\-_\.])vecka[\s\-\.]*\d{1,2}',  # Matches 'vecka46', 'vecka-46', '_vecka_46', etc.
        r'(?:^|[\-_\.])v[\s\-\.]*\d{1,2}',      # Matches 'v46', 'v-46', '_v_46', etc.
        r'(?:^|[\-_\.])w[\s\-\.]*\d{1,2}',      # Matches 'w46', 'w-46', '_w_46', etc.
    ]

    for pattern in week_patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            week_str = match.group()
            # Clean up the string (e.g., remove separators and extra spaces)
            week_str = re.sub(r'[\-_\.]', ' ', week_str)
            week_str = re.sub(r'\s+', ' ', week_str.strip())
            return week_str.capitalize()
    return None

def is_relevant_pdf(url):
    """
    Checks if the PDF URL's filename includes the word 'lunch' or an explicit week number.
    """
    filename = url.split('/')[-1].lower()
    week_number = extract_week_number_from_url(url)
    if 'lunch' in filename or 'dagens' in filename or week_number:
        return True
    return False

def extract_text_with_pypdf2(pdf_content):
    try:
        # Wrap pdf_content in BytesIO to create a file-like object
        pdf_file = BytesIO(pdf_content)

        # Read the PDF content
        reader = PdfReader(pdf_file)
        full_text = ""
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                # Ensure the text is in UTF-8 encoding
                page_text = page_text.encode('utf-8', errors='ignore').decode('utf-8')
                logger.info(f"Extracted text from page {page_num + 1} using PyPDF2:\n{page_text}")
                full_text += page_text + "\n\n"
        return full_text.strip()
    except Exception as e:
        logger.error(f"Error extracting text with PyPDF2: {e}")
        return None

def extract_day_sentences(text):
    """
    Searches for day names in the text and extracts the lines containing them,
    along with the lines before and after.
    """
    # List of day names in Swedish and English
    day_names = [
        'måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
    ]

    # Split the text into lines
    lines = text.split('\n')
    day_lines = []

    for i, line in enumerate(lines):
        if any(day in line.lower() for day in day_names):
            # Get previous, current, and next lines
            prev_line = lines[i - 1] if i > 0 else ''
            next_line = lines[i + 1] if i + 1 < len(lines) else ''
            combined = f"{prev_line}\n{line}\n{next_line}".strip()
            day_lines.append(combined)

    # Remove duplicates
    day_lines = list(set(day_lines))
    return "\n".join(day_lines)

# Functions specific to each solution

def process_pdf_with_solution1(url):
    """
    Solution 1: Uses contour detection and ROI extraction.
    """
    try:
        # Fetch the PDF content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Check content type to confirm it's a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            logger.error(f"The URL does not point to a valid PDF: {url}")
            return None

        pdf_content = response.content

        # Convert PDF to images
        images = pdf_to_images(pdf_content)
        if not images:
            logger.error(f"No images were generated from the PDF at {url}.")
            return None

        # Check if the PDF has more than 2 pages
        if len(images) > 2:
            logger.info(f"Skipping PDF at {url} because it has more than 2 pages.")
            return None

        # Step 1: Extract text from the PDF to find week number and keywords
        week_text = ""
        for i, image in enumerate(images):
            logger.info(f"Extracting text from page {i + 1} of the PDF at {url}...")
            page_text = extract_text_from_image(image)
            if page_text:
                week_text += page_text + "\n\n"

        if not week_text.strip():
            logger.warning(f"No text extracted from the PDF at {url}.")
            return None

        # Extract the week number
        logger.info(f"Extracted text for week number and keyword search:\n{week_text}")
        week_number = extract_week_number(week_text)
        if week_number:
            logger.info(f"Week number found: {week_number}")
        else:
            logger.info("No week number found in the PDF.")

        # Check for keywords in the extracted text
        if any(keyword in week_text.lower() for keyword in ['lunch', 'dagens', 'lunch menu']):
            logger.info("Relevant keyword found in the PDF.")
            proceed_to_step2 = True
        else:
            logger.info("No relevant keywords found in the PDF.")
            proceed_to_step2 = False

        # Decide whether to proceed to step 2
        if week_number or proceed_to_step2:
            # Step 2: Proceed to process the PDF further using contour detection and OCR
            # Reset full_text to extract the menu text
            full_text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i + 1} of the PDF at {url} for menu text...")

                # Preprocess image for contour detection
                thresh_image = preprocess_image_for_contour_detection(image)

                # Find contours
                contours = find_contours(thresh_image)

                # Filter and sort contours
                sorted_contours = filter_and_sort_contours(contours)
                if not sorted_contours:
                    logger.warning(f"No significant contours found on page {i + 1}. Using the whole page for OCR.")
                    page_text = extract_text_from_image(image)
                    if page_text:
                        full_text += page_text + "\n\n"
                    continue

                # Crop image regions based on contours
                rois = crop_image_regions(image, sorted_contours)

                # Extract text from each ROI
                page_text = extract_text_from_rois(rois)
                if page_text:
                    full_text += page_text + "\n\n"

            if not full_text.strip():
                logger.warning(f"No relevant text extracted from the PDF at {url}.")
                return None

            # Combine the week number with the full text
            combined_text = ""
            if week_number:
                combined_text += f"{week_number}\n\n{full_text.strip()}"
            else:
                # Optionally, include a placeholder or omit the week number
                combined_text += f"{full_text.strip()}"

            return combined_text
        else:
            logger.info(f"Neither week number nor relevant keywords found in the PDF at {url}.")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching the PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF from URL: {e}")
        return None

def process_pdf_with_solution2(url):
    """
    Solution 2: Uses PyPDF2 for text extraction and falls back to OCR if needed.
    Improved to handle easily selectable text, remove duplicates, and better organize the output.
    """
    try:
        # Fetch the PDF content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Check content type to confirm it's a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            logger.error(f"The URL does not point to a valid PDF: {url}")
            return None

        pdf_content = response.content

        # Attempt to extract text directly from the PDF using PyPDF2
        pdf_text = extract_text_with_pypdf2(pdf_content)
        if pdf_text and len(pdf_text.strip()) > 50:  # Adjust threshold as needed
            logger.info("PDF contains selectable text. Using PyPDF2 extracted text.")
            # Deduplicate lines and organize content
            cleaned_text = clean_and_organize_text(pdf_text)
            return cleaned_text
        else:
            logger.info("PDF does not contain selectable text or text is insufficient. Proceeding with OCR.")

            # Convert PDF to images and fallback to OCR
            images = pdf_to_images(pdf_content)
            if not images:
                logger.error(f"No images were generated from the PDF at {url}.")
                return None

            # Extract text from images using OCR
            full_text = ""
            for i, image in enumerate(images):
                logger.info(f"Extracting text from page {i + 1} using OCR...")
                page_text = extract_text_from_image(image)
                if page_text:
                    full_text += page_text + "\n\n"

            if not full_text.strip():
                logger.warning(f"No text extracted from the PDF at {url} using OCR.")
                return None

            return full_text.strip()

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching the PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF from URL: {e}")
        return None

def clean_and_organize_text(text):
    """
    Cleans and organizes extracted text by removing duplicates and grouping by sections based on keywords.
    """
    # Split text into lines
    lines = text.splitlines()
    
    # Remove duplicates while preserving order
    seen = set()
    unique_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line and cleaned_line not in seen:
            seen.add(cleaned_line)
            unique_lines.append(cleaned_line)
    
    # Reorganize by sections (e.g., group by day names or "VECKANS" sections)
    organized_text = []
    section = []
    day_keywords = ['TISDAG', 'ONSDAG', 'TORSDAG', 'FREDAG', 'VECKANS']
    
    for line in unique_lines:
        # Start a new section if the line is a day or weekly special
        if any(keyword in line for keyword in day_keywords):
            if section:
                organized_text.append("\n".join(section))
                section = []
        section.append(line)
    
    # Add the last section
    if section:
        organized_text.append("\n".join(section))

    # Join all sections with double newlines for better readability
    return "\n\n".join(organized_text)

    """
    Solution 2: Uses PyPDF2 for text extraction and falls back to OCR if needed.
    """
    try:
        # Fetch the PDF content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Check content type to confirm it's a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            logger.error(f"The URL does not point to a valid PDF: {url}")
            return None

        pdf_content = response.content

        # Attempt to extract text directly from the PDF using PyPDF2
        pdf_text = extract_text_with_pypdf2(pdf_content)
        if pdf_text and len(pdf_text.strip()) > 50:  # Adjust threshold as needed
            logger.info("PDF contains selectable text. Using PyPDF2 extracted text.")
            combined_full_text = pdf_text
        else:
            logger.info("PDF does not contain selectable text or text is insufficient. Proceeding with OCR.")

            # Convert PDF to images
            images = pdf_to_images(pdf_content)
            if not images:
                logger.error(f"No images were generated from the PDF at {url}.")
                return None

            # Extract text from images using OCR
            full_text = ""
            for i, image in enumerate(images):
                logger.info(f"Extracting text from page {i + 1} using OCR...")
                page_text = extract_text_from_image(image)
                if page_text:
                    full_text += page_text + "\n\n"

            if not full_text.strip():
                logger.warning(f"No text extracted from the PDF at {url} using OCR.")
                return None

            combined_full_text = full_text

        # Extract the week number
        week_number = extract_week_number(combined_full_text)
        if not week_number:
            week_number = extract_week_number_from_url(url)

        # Extract sentences containing day names
        day_sentences = extract_day_sentences(combined_full_text)
        if day_sentences:
            logger.info("Day sentences extracted from combined text.")
            # Combine week number and day sentences
            if week_number:
                combined_text = f"{week_number}\n\n{day_sentences}".strip()
            else:
                combined_text = day_sentences.strip()
        else:
            logger.info("No day sentences found in combined text.")
            # Use the full text
            if week_number:
                combined_text = f"{week_number}\n\n{combined_full_text}".strip()
            else:
                combined_text = combined_full_text.strip()

        return combined_text if combined_text.strip() else None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching the PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF from URL: {e}")
        return None

def process_pdf_with_solution3(url):
    """
    Solution 3: Directly performs OCR on the whole image with preprocessing and targeted regions for "Veckans" sections.
    """
    try:
        # Fetch the PDF content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Check content type to confirm it's a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            logger.error(f"The URL does not point to a valid PDF: {url}")
            return None

        pdf_content = response.content

        # Convert PDF to images
        images = pdf_to_images(pdf_content)
        if not images:
            logger.error(f"No images were generated from the PDF at {url}.")
            return None

        # Full text extraction
        full_text = ""
        for i, image in enumerate(images):
            logger.info(f"Extracting text from page {i + 1} using OCR with preprocessing...")
            processed_image = preprocess_image_for_ocr(image)
            page_text = extract_text_from_image(processed_image)
            if page_text:
                full_text += page_text + "\n\n"
            else:
                logger.warning(f"No text extracted from page {i + 1} using OCR.")

        # Extract "Veckans" sections specifically
        veckans_fisk_text = extract_text_from_region(images[0], keyword="Veckans Fisk")
        veckans_vegetariska_text = extract_text_from_region(images[0], keyword="Veckans Vegetariska")

        # Combine extracted parts
        combined_text = full_text + "\n\n" + veckans_fisk_text + "\n\n" + veckans_vegetariska_text
        return combined_text.strip() if combined_text.strip() else None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching the PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF from URL: {e}")
        return None

def extract_text_from_region(image, keyword):
    """
    Extracts text from a specific region of the image based on the keyword (e.g., "Veckans Fisk").
    """
    # Find the approximate region where the keyword is located and extract text from that area
    text = extract_text_from_image(image)
    if keyword in text:
        start_idx = text.find(keyword)
        # Extract text around the keyword (e.g., the following lines or sentences)
        extracted_text = text[start_idx:start_idx + 300]  # Adjust 300 to capture nearby content
        return extracted_text
    return ""

    """
    Solution 3: Directly performs OCR on the whole image with preprocessing to improve accuracy.
    """
    try:
        # Fetch the PDF content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Check content type to confirm it's a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            logger.error(f"The URL does not point to a valid PDF: {url}")
            return None

        pdf_content = response.content

        # Convert PDF to images
        images = pdf_to_images(pdf_content)
        if not images:
            logger.error(f"No images were generated from the PDF at {url}.")
            return None

        # Extract text from images using OCR with preprocessing
        full_text = ""
        for i, image in enumerate(images):
            logger.info(f"Extracting text from page {i + 1} using OCR with preprocessing...")

            # Preprocess the image to improve OCR accuracy
            processed_image = preprocess_image_for_ocr(image)

            # Extract text from the preprocessed image
            page_text = extract_text_from_image(processed_image)
            if page_text:
                full_text += page_text + "\n\n"
            else:
                logger.warning(f"No text extracted from page {i + 1} using OCR.")

        if not full_text.strip():
            logger.warning(f"No relevant text extracted from the PDF at {url}.")
            return None

        # Extract the week number if available
        week_number = extract_week_number(full_text)
        if not week_number:
            week_number = extract_week_number_from_url(url)

        # Extract sentences containing day names or special sections like "Veckans Fisk" and "Veckans Vegetariska"
        day_sentences = extract_day_sentences(full_text)
        veckans_sections = extract_special_sections(full_text, ["Veckans Fisk", "Veckans Vegetariska"])

        # Combine extracted parts
        combined_text = ""
        if week_number:
            combined_text += f"{week_number}\n\n"
        combined_text += day_sentences + "\n\n" + veckans_sections

        return combined_text.strip() if combined_text.strip() else None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching the PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF from URL: {e}")
        return None

def preprocess_image_for_ocr(image):
    """
    Applies preprocessing steps to the image to enhance OCR accuracy.
    """
    # Convert PIL image to grayscale 
    gray_image = image.convert("L")
    # Increase contrast and apply thresholding
    np_image = np.array(gray_image)
    _, thresholded_image = cv2.threshold(np_image, 150, 255, cv2.THRESH_BINARY)

    return Image.fromarray(thresholded_image)

def extract_special_sections(text, section_keywords):
    """
    Extracts special sections from text based on specific keywords (e.g., "Veckans Fisk" or "Veckans Vegetariska").
    """
    sections = []
    for keyword in section_keywords:
        pattern = rf"{keyword}.*?(?=\n[A-Z]|$)"  # Match until the next uppercase line or end of text
        match = re.search(pattern, text, re.DOTALL)
        if match:
            sections.append(match.group().strip())
    return "\n\n".join(sections)

    """
    Solution 3: Directly performs OCR on the whole image.
    """
    try:
        # Fetch the PDF content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Check content type to confirm it's a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            logger.error(f"The URL does not point to a valid PDF: {url}")
            return None

        pdf_content = response.content

        # Convert PDF to images
        images = pdf_to_images(pdf_content)
        if not images:
            logger.error(f"No images were generated from the PDF at {url}.")
            return None

        # Check if the PDF has more than 2 pages
        if len(images) > 2:
            logger.info(f"Skipping PDF at {url} because it has more than 2 pages.")
            return None

        # Extract text from images using OCR
        full_text = ""
        for i, image in enumerate(images):
            logger.info(f"Extracting text from page {i + 1} using OCR...")
            page_text = extract_text_from_image(image)
            if page_text:
                full_text += page_text + "\n\n"
            else:
                logger.warning(f"No text extracted from page {i + 1} using OCR.")

        if not full_text.strip():
            logger.warning(f"No relevant text extracted from the PDF at {url}.")
            return None

        # Extract the week number
        week_number = extract_week_number(full_text)
        if not week_number:
            week_number = extract_week_number_from_url(url)

        # Extract sentences containing day names
        day_sentences = extract_day_sentences(full_text)
        if day_sentences:
            logger.info("Day sentences extracted from combined text.")
            # Combine week number and day sentences
            if week_number:
                combined_text = f"{week_number}\n\n{day_sentences}".strip()
            else:
                combined_text = day_sentences.strip()
        else:
            logger.info("No day sentences found in combined text.")
            # Use the full text
            if week_number:
                combined_text = f"{week_number}\n\n{full_text}".strip()
            else:
                combined_text = full_text.strip()

        return combined_text if combined_text.strip() else None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching the PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF from URL: {e}")
        return None

def process_pdf_auto(url):
    """
    Automatically selects the best solution based on the PDF's characteristics.
    """
    try:
        # Fetch the PDF content
        response = requests.get(url)
        response.raise_for_status()
        pdf_content = response.content

        # Attempt to extract text using PyPDF2 (Solution 2)
        text = extract_text_with_pypdf2(pdf_content)
        if text and len(text.strip()) > 50:  # Threshold can be adjusted
            logger.info("Auto-detection selected Solution 2 (PyPDF2)")
            return process_pdf_with_solution2(url)

        # Convert PDF to images
        images = pdf_to_images(pdf_content)
        if not images:
            logger.error("Failed to convert PDF to images.")
            return None

        # Analyze the image to decide between Solution 1 and Solution 3
        if is_suitable_for_solution1(images[0]):
            logger.info("Auto-detection selected Solution 1 (Contour Detection)")
            return process_pdf_with_solution1(url)
        else:
            logger.info("Auto-detection selected Solution 3 (Direct OCR)")
            return process_pdf_with_solution3(url)

    except Exception as e:
        logger.error(f"Error during automatic PDF processing: {e}")
        return None

def is_suitable_for_solution1(image):
    """
    Analyzes the image to determine if contour detection is appropriate.
    """
    # Preprocess the image
    thresh_image = preprocess_image_for_contour_detection(image)
    contours = find_contours(thresh_image)
    if contours and len(contours) > 10:  # Adjust threshold based on testing
        return True
    else:
        return False

# Functions related to image preprocessing and contour detection

def preprocess_image_for_contour_detection(image):
    # Convert PIL Image to OpenCV format
    cv_image = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    return thresh

def find_contours(thresh_image):
    contours, _ = cv2.findContours(
        thresh_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return contours

def filter_and_sort_contours(contours):
    # Filter contours based on area
    filtered_contours = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        if area > 1000:  # Adjust the threshold as needed
            filtered_contours.append((x, y, w, h))

    # Sort contours top-to-bottom, then left-to-right
    sorted_contours = sorted(filtered_contours, key=lambda b: (b[1], b[0]))
    return sorted_contours

def crop_image_regions(image, contours):
    rois = []
    for (x, y, w, h) in contours:
        roi = image.crop((x, y, x + w, y + h))
        rois.append(roi)
    return rois

def extract_text_from_rois(rois):
    full_text = ""
    for roi in rois:
        text = extract_text_from_image(roi)
        if text:
            full_text += text + "\n"
    return full_text
