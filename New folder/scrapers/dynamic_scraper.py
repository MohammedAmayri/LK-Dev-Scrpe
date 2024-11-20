from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def scrape_dynamic_content(url):
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    # Handle pop-ups and dynamic content
    # Wait for elements to load
    menu_element = driver.find_element_by_id('menu')
    menu_text = menu_element.text
    driver.quit()
    return menu_text
