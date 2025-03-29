from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
import time

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_driver_path = '/path/to/chromedriver'

service = Service(r"D:\ChromeDriver\chromedriver-win64\chromedriver.exe")
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    driver.get('https://www.tapology.com/fightcenter')

    select_element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "group"))
    )
    select = Select(select_element)
    select.select_by_value("major")

    print("Wybrano: Major Org")
    
    time.sleep(2)

    events_container = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fightcenterEvents"))
    )
    links = events_container.find_elements(By.TAG_NAME, 'a')

    all_links = set(links)


    for link in all_links:
        href = link.get_attribute("href")
        event_name = link.text

        if not href or "/fightcenter/events/" not in href:
            continue

        print(f'Link: {href}')
        print('-' * 50)
finally:

    driver.quit()
    

    # while True:
    #     try:
    #         load_more_button = WebDriverWait(driver, 5).until(
    #             EC.element_to_be_clickable((By.ID, "loadMoreButton"))
    #         )
    #         load_more_button.click()
    #         print("Kliknięto Load More")
    #         time.sleep(2) 
    #     except:
    #         print("Brak więcej przycisków")
    #         break