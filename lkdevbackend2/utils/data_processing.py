# data_processing.py
import openai
import json
import logging
import os
import requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables.")
    raise Exception("OPENAI_API_KEY is not set.")
openai.api_key = openai_api_key

def process_menu_text(menu_text, custom_prompt=None):
    if custom_prompt:
        if "{menu_text}" not in custom_prompt:
            prompt = custom_prompt + f'\n\nText:\n"""{menu_text}"""'
        else:
            prompt = custom_prompt.format(menu_text=menu_text)
    else:
        prompt = f"""
Extract the lunch menu for the week from the following text and format it as a JSON array with the following fields:
- "name": Dish name
- "description": Brief description
- "price": Price as a number (no currency symbols)
- "availability": Days when the dish is available (e.g., ["Monday", "Tuesday", "Wednesday"]). Use only the days explicitly mentioned. If no days are mentioned, leave it empty.
- "allergies": Possible food allergies (e.g., 'milk', 'gluten', etc.), if clearly indicated.
- "tags": Relevant tags such as "Vegetarian", "Vegan", "Gluten-Free".
- "week": Week number (e.g., 34 for V34). If no week number is present, send back the first clear date that you see as part of the text (turning it to week number of year 2024).

Additional guidelines:
1. Ignore all items after the word "À la carte at all times", Sometimes also called "Klassiker"
2. Ignore any irrelevant or gibberish data before generating the menus.
3. Do not assign availability to days not explicitly mentioned. If no days are specified, leave "availability" empty.
4. If no allergies or tags are specified, leave those fields as empty lists.
5. For prices, include only the numeric value without currency symbols.
6. Ensure the output is a JSON array with the specified fields.
7. Do not add any new lunch menus not mentioned in the input text.
8. If the week number is of 3 digits, get rid of the last one.
9. If the name gets too long, try to shorten it to 2 to 3 words and put the rest in the description instead.
10. It's extremely important to always remember to add the tags for vegan and vegetarian dishes.
11. if the price for the menu is mentioned, add it to every lunch if its not changed with special price.
12. To make sure that the week number is correct use one or multiple mentioned dates with the days (if exist), use the date knowing its the year 2024 to calculate the week number
13. When the meal name has the word "Veckans vegetariska", this meal is for the whole week." to catch the veg meal for the whole week.
14.if you find Lunch buffe without any day beside that, it means that the lunch buffe is for the whole week" to catch that the lucnh buffe is for the whole week.But it has to say Lunchbuffe not only buffe
15. if the Vegetarian menu does not include any description, do not include it.
16.if the menu expands over multiple weeks, focus on the current week number now its: week 47(take into consideration that its a odd week)
17.take into consideration that some days could include multiple menus.
Text:
\"\"\"{menu_text}\"\"\"

Return only the JSON array with the fields as specified. Do not include any code snippets or code block markers in your response. For availability, use exact weekday names (Monday, Tuesday, etc.).
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that processes menu data."},
                {"role": "user", "content": prompt}],
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
