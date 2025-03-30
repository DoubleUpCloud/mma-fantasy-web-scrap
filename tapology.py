from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
import time
import re

class TapologyScraper:
    def __init__(self, driver_path, website_url):
        self.website_url = website_url
        self.driver = self._setup_driver(driver_path)
    
    def _setup_driver(self, driver_path):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        service = Service(driver_path)
        return webdriver.Chrome(service=service, options=chrome_options)
    
    def open_website(self):
        self.driver.get(self.website_url)
    
    def select_major_org(self):
        select_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "group"))
        )
        select = Select(select_element)
        select.select_by_value("major")
        print("Wybrano: Major Org")
        time.sleep(2)
    
    def get_event_links(self):
        events_container = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "fightcenterEvents"))
        )
        links = events_container.find_elements(By.TAG_NAME, 'a')
        return set(link.get_attribute("href") for link in links if link.get_attribute("href") and "/fightcenter/events/" in link.get_attribute("href"))
    
    def get_event_details(self, url):
        self.driver.get(url)
        event_name = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'h2'))
        ).text
        
        try:
            event_date = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.hidden.md\\:inline"))
            ).text
        except:
            event_date = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.inline.md\\:hidden"))
            ).text
        
        return event_name, event_date
    
    def get_bouts(self):
        """Pobiera walki (bouts) z danej gali.
           Dla każdej walki zwraca słownik zawierający:
             - left_fighter: imię i nazwisko zawodnika po lewej stronie
             - left_record: bilans walk zawodnika po lewej stronie
             - right_fighter: imię i nazwisko zawodnika po prawej stronie
             - right_record: bilans walk zawodnika po prawej stronie
        """
        bouts = []
        # Poczekaj, aż lista walk pojawi się na stronie
        bout_list = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul[data-event-view-toggle-target='list']"))
        )
        bout_items = bout_list.find_elements(By.TAG_NAME, "li")
        record_pattern = re.compile(r'\d+-\d+')
        
        for bout in bout_items:
            try:
                # Pobierz kontenery dla lewego i prawego zawodnika
                left_container = bout.find_element(By.CSS_SELECTOR, "div[id*='_leftBio']")
                right_container = bout.find_element(By.CSS_SELECTOR, "div[id*='_rightBio']")
                
                left_name = left_container.find_element(By.CSS_SELECTOR, "a.link-primary-red").text.strip()
                right_name = right_container.find_element(By.CSS_SELECTOR, "a.link-primary-red").text.strip()
                
                # Szukamy bilansu w elementach <span>
                left_spans = left_container.find_elements(By.TAG_NAME, "span")
                left_record = None
                for span in left_spans:
                    text = span.text.strip()
                    if record_pattern.fullmatch(text):
                        left_record = text
                        break

                right_spans = right_container.find_elements(By.TAG_NAME, "span")
                right_record = None
                for span in right_spans:
                    text = span.text.strip()
                    if record_pattern.fullmatch(text):
                        right_record = text
                        break
                
                bouts.append({
                    "left_fighter": left_name,
                    "left_record": left_record,
                    "right_fighter": right_name,
                    "right_record": right_record
                })
            except Exception as e:
                print(f"Error processing bout: {e}")
        return bouts

    def scrape_events(self):
        self.open_website()
        self.select_major_org()
        event_links = self.get_event_links()
        
        for link in event_links:
            print(f'Przetwarzanie linku: {link}')
            event_name, event_date = self.get_event_details(link)
            print(f"Nazwa wydarzenia: {event_name}")
            print(f"Data wydarzenia: {event_date}")

            bouts = self.get_bouts()
            for bout in bouts:
                print("Bout:")
                print(f"  Lewy zawodnik: {bout['left_fighter']} ({bout['left_record']})")
                print(f"  Prawy zawodnik: {bout['right_fighter']} ({bout['right_record']})")
                print('-' * 50)
    
    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    driver_path = r"D:\\ChromeDriver\\chromedriver-win64\\chromedriver.exe"
    website_url = 'https://www.tapology.com/fightcenter'
    
    scraper = TapologyScraper(driver_path, website_url)
    try:
        scraper.scrape_events()
    finally:
        scraper.close()


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