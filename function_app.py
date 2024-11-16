import azure.functions as func
from flask import Flask, request, jsonify, render_template
from scrapers.text_scraper import scrape_text
from scrapers.image_scraper import scrape_image
from scrapers.pdf_scraper import scrape_pdf
from scrapers.facebook_scraper import scrape_facebook_post
from scrapers.dynamic_scraper import scrape_dynamic_content
from utils.data_processing import process_menu_text
from dotenv import load_dotenv
import os
import logging
import openai

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables.")
    raise Exception("OPENAI_API_KEY is not set.")
openai.api_key = openai_api_key

# Serve the frontend HTML page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape-menu', methods=['GET'])
def scrape_menu():
    format = request.args.get('format')
    link = request.args.get('link')
    solution = request.args.get('solution')

    if not format or not link:
        return jsonify({'error': 'Missing format or link parameter'}), 400

    logger.info(f"Received request with format: {format}, link: {link}, solution: {solution}")

    try:
        # Scrape menu based on format and solution
        if format.upper() == 'PDF':
            menu_text = scrape_pdf(link, solution)
        elif format.upper() == 'TEXT':
            menu_text = scrape_text(link)
        elif format.upper() == 'IMAGE':
            menu_text = scrape_image(link)
        elif format.upper() == 'FACEBOOK POST':
            menu_text = scrape_facebook_post(link)
        elif format.upper() == 'DYNAMIC':
            menu_text = scrape_dynamic_content(link)
        else:
            return jsonify({'error': f"Unsupported format: {format}"}), 400

        if not menu_text:
            return jsonify({'error': 'Failed to retrieve menu text'}), 500

        # Log the scraped menu text before processing
        logger.info(f"Scraped menu text: {menu_text}")

        # Process menu text
        lunch_menus = process_menu_text(menu_text)

        if not lunch_menus:
            return jsonify({'error': 'Failed to process menu text'}), 500

        # Log the processed menu data
        logger.info(f"Processed menu data: {lunch_menus}")

        return jsonify({'lunch_menus': lunch_menus}), 200

    except ImportError as e:
        logger.error(f"Import error: {e}")
        return jsonify({'error': 'A module or function could not be imported. Please check your setup.'}), 500
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({'error': 'An error occurred while processing the request'}), 500


# Azure Function HTTP trigger handler
def main(req: func.HttpRequest) -> func.HttpResponse:
    # Create a Flask context and use it to call the Flask app
    with app.test_request_context(req.method, path=req.url, data=req.get_data()):
        return app.full_dispatch_request()

