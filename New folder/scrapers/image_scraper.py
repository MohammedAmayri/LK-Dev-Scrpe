import requests
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
import logging
from io import BytesIO
import cv2
import numpy as np
import re

# Configure logging
logger = logging.getLogger(__name__)

# Set the path to the Tesseract executable (adjust the path as needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\mohammed.amayri\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def scrape_image(url):
    """
    Scrapes images from the provided URL, filters based on size and relevance,
    and extracts text from the identified lunch menu image using OCR.
    """
    try:
        # Fetch the webpage content
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.content

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')

        if not img_tags:
            logger.info("No images found on the page.")
            return None

        extracted_texts = []
        for img_tag in img_tags:
            img_url = img_tag.get('src')
            if not img_url:
                continue

            # Handle relative URLs
            img_url = requests.compat.urljoin(url, img_url)

            logger.info(f"Processing image: {img_url}")

            # Download and check image
            image_content = download_image(img_url)
            if not image_content:
                logger.warning(f"Failed to download image: {img_url}")
                continue

            # Open the image and check dimensions
            try:
                image = Image.open(BytesIO(image_content))
                if not is_proper_image(image):  # Skipping logos and other small images
                    logger.info(f"Skipping image due to size constraints: {img_url}")
                    continue
            except Exception as e:
                logger.warning(f"Failed to open image {img_url}: {e}")
                continue

            # Extract text from the image
            text = process_image_for_menu_text(image)
            if text:
                logger.info(f"Extracted text from image (length: {len(text)}).")
                extracted_texts.append(text)
            else:
                logger.info(f"No relevant text extracted from image: {img_url}")

        if extracted_texts:
            combined_text = "\n\n".join(extracted_texts)
            logger.info("Extracted text from images is ready for further processing.")
            return combined_text
        else:
            logger.info("No relevant text extracted from any images.")
            return None

    except Exception as e:
        logger.error(f"An error occurred while scraping images from {url}: {e}")
        return None

def download_image(img_url):
    try:
        response = requests.get(img_url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Failed to download image {img_url}: {e}")
        return None

def is_proper_image(image):
    """
    Filters images based on size to exclude small, irrelevant ones.
    """
    min_width, min_height = 400, 400  # Adjust based on typical menu image size
    width, height = image.size
    return width >= min_width and height >= min_height

def process_image_for_menu_text(image):
    """
    Processes the image to extract menu text using OCR, with targeted keyword
    matching for "Veckans" sections and weekday names.
    """
    try:
        # Preprocess image for OCR
        processed_image = preprocess_image_for_ocr(image)

        # Use Tesseract OCR to extract text
        custom_oem_psm_config = r'--oem 1 --psm 6'
        text = pytesseract.image_to_string(processed_image, lang='swe', config=custom_oem_psm_config)

        # Check for relevant keywords to confirm it's a menu
        keywords = [
            'lunchmeny', 'veckans', 'meny', 'måndag', 'tisdag', 'onsdag', 
            'torsdag', 'fredag', 'lördag', 'söndag', 'serveras', 'pris'
        ]
        if contains_keyword(text, keywords):
            return text
        else:
            logger.info("No relevant keywords detected in the text.")
            return None
    except Exception as e:
        logger.error(f"Failed to extract text from image: {e}")
        return None

def preprocess_image_for_ocr(image):
    """
    Applies preprocessing steps to the image to enhance OCR accuracy.
    """
    # Convert to grayscale
    gray_image = image.convert("L")
    np_image = np.array(gray_image)

    # Resize to improve OCR accuracy
    np_image = cv2.resize(np_image, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    # Apply bilateral filter to reduce noise while preserving edges
    np_image = cv2.bilateralFilter(np_image, 9, 75, 75)

    # Thresholding to create a binary image
    _, np_image = cv2.threshold(np_image, 150, 255, cv2.THRESH_BINARY)

    return Image.fromarray(np_image)

def contains_keyword(text, keywords):
    """
    Checks if the text contains any of the keywords.
    """
    for keyword in keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            return True
    return False
