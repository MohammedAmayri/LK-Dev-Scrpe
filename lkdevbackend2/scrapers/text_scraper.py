import requests
from bs4 import BeautifulSoup
import re

def scrape_text(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    # Extract all text from the page
    page_text = soup.get_text(separator=' ')
    
    # Remove all newlines and tabs
    cleaned_text = ' '.join(page_text.split())
    
    # Define day names in Swedish and English
    day_names = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
        "Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"
    ]

    # Create a regular expression pattern to match any day name
    day_pattern = r"\b(" + "|".join(day_names) + r")\b"

    # Insert a newline before each day name match
    cleaned_text = re.sub(day_pattern, r"\n for the day : \1", cleaned_text)

    return cleaned_text
