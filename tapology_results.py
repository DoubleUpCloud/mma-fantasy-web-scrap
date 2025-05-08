from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
import time
import re
import requests
import json
from datetime import datetime, timedelta

today = datetime.today().date()
yesterday = today - timedelta(days=1)

class TapologyResultsScraper:
    def __init__(self, driver_path, website_url):
        self.website_url = website_url
        self.driver = self._setup_driver(driver_path)
        self.today = datetime.now().date()
        self.yesterday = self.today - timedelta(days=1)

    def _setup_driver(self, driver_path):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

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

    def select_results(self):
        select_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "schedule"))
        )
        select = Select(select_element)
        select.select_by_value("results")
        print("Wybrano: Results")
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
            location = self.driver.find_element(By.CSS_SELECTOR, "div.hidden.md\\:inline a.link-primary-gray").text

        except:
            event_date = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.inline.md\\:hidden"))
            ).text

            location = self.driver.find_element(By.CSS_SELECTOR, "div.inline.md\\:hidden a.link-primary-gray").text

        # Parse the event date to check if it's from today or yesterday
        try:
            # Example format: "Sat, 05.18.2024"
            date_parts = event_date.split(", ")[1].split(".")
            month = int(date_parts[0])
            day = int(date_parts[1])
            year = int(date_parts[2])
            event_date_obj = datetime.date(year, month, day)

            # Check if the event date is today or yesterday
            if event_date_obj != self.today and event_date_obj != self.yesterday:
                return None, None, None
        except Exception as e:
            print(f"Error parsing date: {e}")
            # If we can't parse the date, we'll include the event anyway
            pass

        return event_name, event_date, location

    def get_bout_results(self):
        bouts = []
        bout_items = []
        try:
            # Try to find the results container based on the HTML example in the issue description
            # First try the exact CSS selector from the example
            try:
                bout_items = self.driver.find_elements(By.CSS_SELECTOR, "div.div.px-2.py-2\\.5.text-xs.leading-none.flex.justify-between")
            except:
                # If that fails, try a more general selector
                bout_items = self.driver.find_elements(By.CSS_SELECTOR, "div.px-2.py-2\\.5.text-xs.leading-none.flex.justify-between")

            if not bout_items:
                # If still no results, try another approach
                results_section = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-event-view-toggle-target='list']"))
                )
                bout_items = results_section.find_elements(By.CSS_SELECTOR, "li")

        except Exception as e:
            print(f"Error finding bout results: {e}")
            return bouts

        for bout in bout_items:
            try:
                # Scroll to the bout
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", bout)
                time.sleep(0.2)

                # Try to get the left and right spans
                try:
                    left_span = bout.find_element(By.CSS_SELECTOR, "span.left")
                    right_span = bout.find_element(By.CSS_SELECTOR, "span.right")
                except:
                    # If the spans aren't found, this might not be a result item
                    continue

                left_text = left_span.text
                result_details = right_span.text

                # Parse the left text to extract winner and loser
                if "def" in left_text:
                    parts = left_text.split("def")
                    winner_text = parts[0].strip()
                    loser_text = parts[1].strip()

                    # Clean up the winner and loser names (remove W/L indicators)
                    winner = re.sub(r'^\s*W\s*', '', winner_text).strip()
                    loser = re.sub(r'^\s*L\s*', '', loser_text).strip()

                    # Get fighter links
                    fighter_links = left_span.find_elements(By.TAG_NAME, "a")
                    winner_link = ""
                    loser_link = ""
                    if len(fighter_links) >= 2:
                        winner_link = fighter_links[0].get_attribute("href")
                        loser_link = fighter_links[1].get_attribute("href")

                    # Get result link
                    result_link = ""
                    result_links = right_span.find_elements(By.TAG_NAME, "a")
                    if result_links:
                        result_link = result_links[0].get_attribute("href")

                    # Check for W/L indicators
                    winner_indicator = "W" if "W" in winner_text else ""
                    loser_indicator = "L" if "L" in loser_text else ""

                    bouts.append({
                        "winner": winner,
                        "loser": loser,
                        "result": result_details,
                    })
            except Exception as e:
                print(f"Error processing bout result: {e}")
                print("HTML:")
                print(bout.text)

        return bouts

    def scrape_results(self):
        self.open_website()
        self.select_major_org()
        self.select_results()
        event_links = self.get_event_links()

        results_data = []

        for link in event_links:
            print(f'Przetwarzanie linku: {link}')
            event_name, event_date, event_place = self.get_event_details(link)

            # Skip events that are not from today or yesterday
            if event_date is None:
                print(f"Skipping event: {link}")
                continue

            # print(event_date)
            # try:
            #     event_dt=datetime.strptime(event_date, "%B %d, %Y").date()
            # except ValueError:
            #     print(f"Skipping event: (nieprawidlowy format daty")
            #     continue
            #
            # if event_dt not in (today,yesterday):
            #     print(f"Skipping event (nie z dziś ani wczoraj): {link}")
            #     continue

            print(f"Nazwa wydarzenia: {event_name}")
            print(f"Data wydarzenia: {event_date}")
            print(f"Miejsce wydarzenia: {event_place}")

            bout_results = self.get_bout_results()
            for bout in bout_results:
                print("Bout Result:")
                print(f"  Result: {bout['result']}")
                print('-' * 50)

            # Create event data
            event_data = {
                "name": event_name,
                "date": event_date,
                "location": event_place,
                "bout_results": bout_results
            }

            results_data.append(event_data)

            # Send the scraped event data to the backend
            self.send_event_data(event_name, event_date, event_place, bout_results)

        return results_data

    def send_event_data(self, event_name, event_date, event_place, bout_results):
        event_data = {
            "name": event_name,
            "date": event_date,
            "location": event_place,
            "bout_results": bout_results
        }
        print(event_data)
        try:
            response = requests.post(
                "http://localhost:8080/api/event-results",
                json=event_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200 or response.status_code == 201:
                print(f"Successfully sent results data to backend for event: {event_name}")
            else:
                print(f"Failed to send results data to backend. Status code: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error sending results data to backend: {e}")

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    driver_path = r"D:\\ChromeDriver\\chromedriver-win64\\chromedriver.exe"
    website_url = 'https://www.tapology.com/fightcenter'

    scraper = TapologyResultsScraper(driver_path, website_url)
    try:
        scraper.scrape_results()
    finally:
        scraper.close()
