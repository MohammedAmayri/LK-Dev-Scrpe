import requests
import os
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env file into the environment

def scrape_facebook_post(page_url):
    access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
    if not access_token:
        print("Facebook access token not set.")
        return None

    # Extract the page ID or username from the URL
    if 'facebook.com/' not in page_url:
        print("Invalid Facebook page URL.")
        return None

    page_identifier = page_url.split('facebook.com/')[-1].split('/')[0]

    # Use Facebook Graph API to get the latest posts
    api_url = f"https://graph.facebook.com/v12.0/{page_identifier}/posts"
    params = {
        'access_token': access_token,
        'fields': 'message',
        'limit': 5  # Fetch the latest 5 posts
    }
    response = requests.get(api_url, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch posts from Facebook: {response.json().get('error', {})}")
        return None

    data = response.json()
    posts = data.get('data', [])

    for post in posts:
        message = post.get('message', '').lower()
        if 'lunch' in message or 'dagens' in message:
            return post['message']

    print("No recent posts containing 'lunch' or 'dagens' found.")
    return None
