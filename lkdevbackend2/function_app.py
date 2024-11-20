import logging
import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import openai

from .scrapers.text_scraper import scrape_text
from .scrapers.image_scraper import scrape_image
from .scrapers.pdf_scraper import scrape_pdf
from .scrapers.facebook_scraper import scrape_facebook_post
from .scrapers.dynamic_scraper import scrape_dynamic_content
from .utils.data_processing import process_menu_text

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables.")
    raise Exception("OPENAI_API_KEY is not set.")
openai.api_key = openai_api_key


@app.route("/")
def index():
    """Serve the index page."""
    logger.info("Serving index page.")
    return render_template("index.html")


@app.route("/scrape-menu", methods=["GET"])
def scrape_menu():
    """
    Endpoint to scrape a menu based on the provided format and link.
    Query Parameters:
        - format: Menu format (PDF, TEXT, IMAGE, etc.)
        - link: URL to scrape
        - solution: (Optional) Additional parameter for certain formats
    """
    format = request.args.get("format")
    link = request.args.get("link")
    solution = request.args.get("solution")

    # Validate required parameters
    if not format or not link:
        logger.warning("Missing 'format' or 'link' parameter.")
        return jsonify({"error": "Missing 'format' or 'link' parameter"}), 400

    logger.info(f"Received request: format={format}, link={link}, solution={solution}")

    try:
        # Dispatch the request based on the format
        if format.upper() == "PDF":
            menu_text = scrape_pdf(link, solution)
        elif format.upper() == "TEXT":
            menu_text = scrape_text(link)
        elif format.upper() == "IMAGE":
            menu_text = scrape_image(link)
        elif format.upper() == "FACEBOOK POST":
            menu_text = scrape_facebook_post(link)
        elif format.upper() == "DYNAMIC":
            menu_text = scrape_dynamic_content(link)
        else:
            logger.warning(f"Unsupported format: {format}")
            return jsonify({"error": f"Unsupported format: {format}"}), 400

        # If scraping failed
        if not menu_text:
            logger.error("Failed to retrieve menu text.")
            return jsonify({"error": "Failed to retrieve menu text"}), 500

        # Process the scraped text into structured menu data
        lunch_menus = process_menu_text(menu_text)

        # If processing failed
        if not lunch_menus:
            logger.error("Failed to process menu text.")
            return jsonify({"error": "Failed to process menu text"}), 500

        # Return the processed lunch menus
        logger.info(f"Processed menu data: {lunch_menus}")
        return jsonify({"lunch_menus": lunch_menus}), 200

    except Exception as e:
        logger.exception("Error processing scrape-menu request.")
        return jsonify({"error": "An internal error occurred while processing the request"}), 500


@app.route("/api/lkdevbackend2", methods=["GET", "POST"])
def lkdevbackend2():
    """
    Main route for processing API requests.
    Query Parameters:
        - format: Menu format (PDF, TEXT, IMAGE, etc.)
        - link: URL to scrape
        - solution: (Optional) Additional parameter for certain formats
    """
    logger.info("Processing lkdevbackend2 request.")

    format = request.args.get("format")
    link = request.args.get("link")
    solution = request.args.get("solution")

    # Validate required parameters
    if not format or not link:
        logger.warning("Missing 'format' or 'link' parameter.")
        return jsonify({"error": "Missing 'format' or 'link' parameter"}), 400

    logger.info(f"Received request: format={format}, link={link}, solution={solution}")

    try:
        # Dispatch the request based on the format
        if format.upper() == "PDF":
            menu_text = scrape_pdf(link, solution)
        elif format.upper() == "TEXT":
            menu_text = scrape_text(link)
        elif format.upper() == "IMAGE":
            menu_text = scrape_image(link)
        elif format.upper() == "FACEBOOK POST":
            menu_text = scrape_facebook_post(link)
        elif format.upper() == "DYNAMIC":
            menu_text = scrape_dynamic_content(link)
        else:
            logger.warning(f"Unsupported format: {format}")
            return jsonify({"error": f"Unsupported format: {format}"}), 400

        # If scraping failed
        if not menu_text:
            logger.error("Failed to retrieve menu text.")
            return jsonify({"error": "Failed to retrieve menu text"}), 500

        # Process the scraped text into structured menu data
        lunch_menus = process_menu_text(menu_text)

        # If processing failed
        if not lunch_menus:
            logger.error("Failed to process menu text.")
            return jsonify({"error": "Failed to process menu text"}), 500

        # Return the processed lunch menus
        logger.info(f"Processed menu data: {lunch_menus}")
        return jsonify({"lunch_menus": lunch_menus}), 200

    except Exception as e:
        logger.exception("Error processing lkdevbackend2 request.")
        return jsonify({"error": "An internal error occurred while processing the request"}), 500
