import os
from dotenv import load_dotenv
import logging
from utils.database import restaurants_collection, update_restaurant_menus
from utils.data_processing import process_menu_text
from scrapers.text_scraper import scrape_text
from scrapers.image_scraper import scrape_image
from scrapers.pdf_scraper import scrape_pdf
from scrapers.facebook_scraper import scrape_facebook_post
from scrapers.dynamic_scraper import scrape_dynamic_content

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_update_menus():
    # Fetch restaurants that need updating
    restaurants = restaurants_collection.find({
        'menuPeriodicity': {'$ne': 'Never'}
    })

    for restaurant in restaurants:
        try:
            logger.info(f"Processing restaurant: {restaurant['name']}")
            lunch_link = restaurant.get('lunch_link')
            lunch_format = restaurant.get('lunch_format')
            restaurant_id = restaurant['_id']

            if not lunch_link or not lunch_format:
                logger.warning(f"Skipping {restaurant['name']} due to missing lunch_link or lunch_format.")
                continue

            # Scrape menu based on format
            if lunch_format.upper() == 'TEXT':
                menu_text = scrape_text(lunch_link)
            elif lunch_format.upper() == 'IMAGE':
                menu_text = scrape_image(lunch_link)
            elif lunch_format.upper() == 'PDF':
                menu_text = scrape_pdf(lunch_link)
            elif lunch_format.upper() == 'FACEBOOK POST':
                menu_text = scrape_facebook_post(lunch_link)
            elif lunch_format.upper() == 'DYNAMIC':
                menu_text = scrape_dynamic_content(lunch_link)
            else:
                logger.warning(f"Unsupported lunch_format for {restaurant['name']}: {lunch_format}")
                continue

            if not menu_text:
                logger.warning(f"No menu text found for {restaurant['name']}")
                continue

            # Process menu text
            lunch_menus = process_menu_text(menu_text)

            if not lunch_menus:
                logger.warning(f"Failed to process menu for {restaurant['name']}")
                continue

            # Update database
            updated_count = update_restaurant_menus(restaurant_id, lunch_menus)
            if updated_count > 0:
                logger.info(f"Updated menu for {restaurant['name']}")
            else:
                logger.info(f"No changes made to {restaurant['name']}")

        except Exception as e:
            logger.error(f"Error processing {restaurant['name']}: {e}")

if __name__ == "__main__":
    fetch_and_update_menus()
