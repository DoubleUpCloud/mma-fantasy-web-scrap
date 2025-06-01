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


class TapologyResultsScraper:
    def __init__(self, driver_path, website_url):
        self.website_url = website_url
        self.driver = self._setup_driver(driver_path)
        self.today = datetime.now().date()
        # Ustawienie daty 'twenty_days_ago' na 20 dni wstecz od dziś
        self.twenty_days_ago = self.today - timedelta(days=1)

    def _setup_driver(self, driver_path):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

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
        return set(link.get_attribute("href") for link in links if
                   link.get_attribute("href") and "/fightcenter/events/" in link.get_attribute("href"))

    def get_event_details(self, url):
        self.driver.get(url)
        event_name = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'h2'))
        ).text

        event_date = None
        location = None

        try:
            event_date_span = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.hidden.md\\:inline, span.inline.md\\:hidden"))
            )
            event_date = event_date_span.text
        except Exception as e:
            print(f"Nie znaleziono elementu daty wydarzenia: {e}")

        try:
            location_element = self.driver.find_element(By.CSS_SELECTOR,
                                                        "div.hidden.md\\:inline a.link-primary-gray, div.inline.md\\:hidden a.link-primary-gray")
            location = location_element.text
        except Exception as e:
            print(f"Nie znaleziono elementu lokalizacji: {e}")

        if event_date:
            try:
                # Próba parsowania formatu "MAJ 24, 2025"
                try:
                    event_date_obj = datetime.strptime(event_date, "%B %d, %Y").date()
                except ValueError:
                    # Próba parsowania formatu "05.24.2025" lub podobnego
                    date_parts = event_date.split(".")
                    if len(date_parts) == 3:
                        month = int(date_parts[0])
                        day = int(date_parts[1])
                        year = int(date_parts[2])
                        event_date_obj = datetime.date(year, month, day)
                    else:
                        raise ValueError(f"Nieznany format daty: {event_date}")

                # Zmieniony warunek: Sprawdź, czy data wydarzenia jest w zakresie ostatnich 20 dni (włącznie)
                if not (self.twenty_days_ago <= event_date_obj <= self.today):
                    print(f"Pominięcie wydarzenia poza zakresem dat: {event_name} ({event_date})")
                    return None, None, None
            except Exception as e:
                print(
                    f"Błąd podczas parsowania lub sprawdzania daty: {event_date}: {e}. Kontynuuję przetwarzanie wydarzenia.")
                pass

        return event_name, event_date, location

    def get_fighter_full_name(self, fighter_profile_url):
        if not fighter_profile_url:
            return "", "0-0-0"  # Zwracamy pusty string dla imienia i rekordu

        current_url = self.driver.current_url
        self.driver.get(fighter_profile_url)
        full_name = ""
        record = "0-0-0"
        try:
            # Selektor dla pełnego imienia i nazwiska (najnowsza strategia)
            name_element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH,
                                                "//div[@id='specOwnershipSidebarClaimSection']//div[@class='div inline-block text-[17px] leading-none font-bold text-tap_3 mb-2.5']"))
            )
            full_name = name_element.text.strip()
            # print(f"Pobrano imię: {full_name}")

        except Exception as e:
            print(f"Nie udało się pobrać imienia/rekordu zawodnika z {fighter_profile_url}: {e}")
        finally:
            self.driver.get(current_url)
        return full_name, record

    def get_bout_results(self):
        bouts_info = []
        try:
            bout_items = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((
                    By.XPATH,
                    "//div[contains(@class, 'eventQuickCardSidebar')]/div[contains(@class, 'px-2') and contains(@class, 'py-2.5') and contains(@class, 'flex') and contains(@class, 'justify-between')]"
                ))
            )

            for bout in bout_items:
                try:
                    left_span = bout.find_element(By.CSS_SELECTOR, "span.left")
                    right_span = bout.find_element(By.CSS_SELECTOR, "span.right")

                    left_text = left_span.text
                    result_details = right_span.text

                    winner_link = ""
                    loser_link = ""

                    fighter_links = left_span.find_elements(By.TAG_NAME, "a")
                    if len(fighter_links) >= 2:
                        winner_link = fighter_links[0].get_attribute("href")
                        loser_link = fighter_links[1].get_attribute("href")
                    elif len(fighter_links) == 1:
                        if "def" in left_text.lower():
                            winner_link = fighter_links[0].get_attribute("href")
                        else:
                            pass

                    bouts_info.append({
                        "left_text": left_text,
                        "result_details": result_details,
                        "winner_link": winner_link,
                        "loser_link": loser_link
                    })
                except Exception as e:
                    print(f"Błąd podczas zbierania wstępnych danych walki (wewnątrz pętli): {e}")
                    continue

        except Exception as e:
            print(f"Błąd podczas znajdowania głównych elementów walk (bout_items): {e}")
            return []

        return bouts_info

    def scrape_results(self):
        self.open_website()
        self.select_major_org()
        self.select_results()
        event_links = self.get_event_links()

        results_data = []

        for link in event_links:
            print(f'Przetwarzanie linku: {link}')
            event_name, event_date, event_place = self.get_event_details(link)

            if event_name is None:
                continue

            print(f"Nazwa wydarzenia: {event_name}")
            print(f"Data wydarzenia: {event_date}")
            print(f"Miejsce wydarzenia: {event_place}")

            raw_bout_data = self.get_bout_results()

            processed_bouts = []
            for bout_data in raw_bout_data:
                winner_link = bout_data['winner_link']
                loser_link = bout_data['loser_link']
                left_text = bout_data['left_text']
                result_details = bout_data['result_details']

                winner_full_name = ""
                winner_record = ""
                loser_full_name = ""
                loser_record = ""

                # Przejdź do profilu zwycięzcy i pobierz pełne imię i rekord
                if winner_link:
                    winner_full_name, winner_record = self.get_fighter_full_name(winner_link)
                # Przejdź do profilu przegranego i pobierz pełne imię i rekord
                if loser_link:
                    loser_full_name, loser_record = self.get_fighter_full_name(loser_link)

                winner = winner_full_name
                loser = loser_full_name

                # Fallback na parsowanie z tekstu, jeśli pełne imiona nie zostały znalezione
                if not winner or not loser:
                    match = re.search(r'(.*)\s+def\s+(.*)', left_text, re.IGNORECASE)
                    if match:
                        winner_text_raw = match.group(1).strip()
                        loser_text_raw = match.group(2).strip()
                        if not winner:
                            winner = re.sub(r'^\s*[WL]\s*', '', winner_text_raw).strip()
                        if not loser:
                            loser = re.sub(r'^\s*[WL]\s*', '', loser_text_raw).strip()
                    else:
                        fighter_names_from_text = [n.strip() for n in re.split(r'\s+vs\.?\s+', left_text) if n.strip()]
                        if len(fighter_names_from_text) >= 2:
                            if not winner:
                                winner = fighter_names_from_text[0]
                            if not loser:
                                loser = fighter_names_from_text[1]
                        elif len(fighter_names_from_text) == 1:
                            if not winner:
                                winner = fighter_names_from_text[0]

                processed_bouts.append({
                    "winner": winner,
                    "winner_record": winner_record,  # Dodano rekord zwycięzcy
                    "loser": loser,
                    "loser_record": loser_record,  # Dodano rekord przegranego
                    "result": result_details,
                })

            # for bout in processed_bouts:
            #     print("Wynik walki:")
            #     print(f"  Zwycięzca: {bout['winner']} (Rekord: {bout['winner_record']})")
            #     print(f"  Przegrany: {bout['loser']} (Rekord: {bout['loser_record']})")
            #     print(f"  Rezultat: {bout['result']}")
            #     print('-' * 50)

            event_data = {
                "name": event_name,
                "date": event_date,
                "location": event_place,
                "bout_results": processed_bouts
            }

            results_data.append(event_data)

            self.send_event_data(event_name, event_date, event_place, processed_bouts)

            self.driver.get(link)

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
                print(f"Pomyślnie wysłano dane do backendu dla wydarzenia: {event_name}")
            else:
                print(f"Nie udało się wysłać danych do backendu. Status code: {response.status_code}")
                print(f"Odpowiedź: {response.text}")
        except Exception as e:
            print(f"Błąd podczas wysyłania danych do backendu: {e}")

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