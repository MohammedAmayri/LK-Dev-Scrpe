import openai
import json
import logging
import certifi
import os
from datetime import datetime, timedelta
import requests.exceptions
import requests
import ssl

# Set SSL_CERT_FILE environment variable
os.environ["SSL_CERT_FILE"] = certifi.where()
print("SSL_CERT_FILE set to:", os.environ["SSL_CERT_FILE"])
print(certifi.where())

print("SSL default verify paths:")
print(ssl.get_default_verify_paths())
ssl._create_default_https_context = ssl.create_default_context
ssl._create_default_https_context().load_verify_locations(certifi.where())
print(ssl.OPENSSL_VERSION)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure OpenAI uses certifi's CA bundle for SSL verification
openai.verify_ssl = certifi.where()

# Set OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables.")
    raise Exception("OPENAI_API_KEY is not set.")
openai.api_key = openai_api_key

def process_menu_text(menu_text):
    prompt = f"""
Extract the lunch menu for the week from the following text and format it as a JSON array with the following fields:
- "name": Dish name
- "description": Brief description
- "price": Price as a number (no currency symbols)
- "availability": Days when the dish is available (e.g., ["Monday", "Tuesday", "Wednesday"]). Use only the days explicitly mentioned. If no days are mentioned, leave it empty.
- "allergies": Possible food allergies (e.g., 'milk', 'gluten', etc.), if clearly indicated.
- "tags": Relevant tags such as "Vegetarian", "Vegan", "Gluten-Free".
- "week": Week number (e.g., 34 for V34). If no week number is present, send back the first clear date that you see as part of the text(turning it to week number of year 2024).

Additional guidelines:
1. Ignore all items after the word "À la carte at all times".
2. Ignore any irrelevant or gibberish data before generating the menus.
3. Do not assign availability to days not explicitly mentioned. If no days are specified, leave "availability" empty.
4. If no allergies or tags are specified, leave those fields as empty lists.
5. For prices, include only the numeric value without currency symbols.
6. Ensure the output is a JSON array with the specified fields.
7. Do not add any new lunch menus not mentioned in the input text.
8. If the week number is of 3 digits, get rid of the last one.
9. if the name gets too long. try to shorten it to 2 to 3 words and put the rest in the description instead.
10. its extremly important to always remebmer to add the tags for the vegan and vegeterian dishes.

Text:
\"\"\"{menu_text}\"\"\"

Return only the JSON array with the fields as specified. Do not include any code snippets or code block markers in your response. For availability, use exact weekday names (Monday, Tuesday, etc.).
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that processes menu data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.0,
        )

        # Log the response from OpenAI for debugging
        logger.info(f"OpenAI response: {response}")

        # Validate response structure and extract the assistant's message
        if "choices" in response and response["choices"]:
            assistant_message = response['choices'][0]['message']['content'].strip()
            logger.debug(f"Assistant's response content: {assistant_message}")
        else:
            logger.error("Unexpected response format or empty choices.")
            return None

        # Clean the assistant's message by removing code block markers if present
        if assistant_message.startswith("```") and assistant_message.endswith("```"):
            assistant_message = assistant_message[3:-3].strip()
            # Remove language identifier if present
            if assistant_message.startswith("json"):
                assistant_message = assistant_message[4:].strip()

        # Attempt to parse the cleaned message as JSON
        menu_data = json.loads(assistant_message)

        # Add dates based on the week number
        menu_data = add_dates_to_menu(menu_data)
        return menu_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Assistant message content that failed to parse: {assistant_message}")
        return None
    except requests.exceptions.SSLError as ssl_error:
        logger.error(f"SSL Error: {ssl_error}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in process_menu_text: {e}")
        return None

def add_dates_to_menu(menu_data):
    # Map day names to their offsets within the week
    day_offsets = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6
    }

    for item in menu_data:
        if "week" in item:
            try:
                week_number = int(item["week"])
                current_year = datetime.now().year
                # Calculate the start date of the week (Monday)
                start_date = datetime.strptime(f"{current_year}-W{week_number}-1", "%Y-W%W-%w")

                availability = item.get("availability", [])

                # If availability is empty, assume Monday to Friday
                if not availability:
                    availability = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                    item["availability"] = availability  # Update the item

                # Collect dates of availability days
                availability_dates = []

                for day in availability:
                    if day in day_offsets:
                        # Calculate the date for this specific day
                        day_date = start_date + timedelta(days=day_offsets[day])
                        availability_dates.append(day_date)
                    else:
                        logger.warning(f"Unknown day '{day}' in availability for item '{item.get('name')}'")

                if availability_dates:
                    # Set validFrom to the earliest date
                    valid_from_date = min(availability_dates)
                    # Set validTo to the latest date
                    valid_to_date = max(availability_dates)
                    item["validFrom"] = {"$date": valid_from_date.isoformat()}
                    item["validTo"] = {"$date": valid_to_date.isoformat()}
                else:
                    # Handle cases where no valid dates are found
                    logger.warning(f"No valid dates found for item '{item.get('name')}'")
                    item["validFrom"] = {"$date": None}
                    item["validTo"] = {"$date": None}
                
                # Optionally remove the "week" field if you no longer need it
                del item["week"]

            except ValueError as e:
                logger.error(f"Failed to convert week number to dates: {e}")

    return menu_data
