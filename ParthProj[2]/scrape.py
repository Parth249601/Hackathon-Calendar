from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
from datetime import datetime
import re
import platform
import os

class Hackathon:
    def __init__(self, name, registration_start, registration_end, location, prize, participants, registration_link):
        self.name = name
        self.registration_start = registration_start
        self.registration_end = registration_end
        self.location = location
        self.prize = prize
        self.participants = participants
        self.registration_link = registration_link

    def __str__(self):
        return (f"Hackathon Name: {self.name}\n"
                f"Registration Start: {self.registration_start}\n"
                f"Registration End: {self.registration_end}\n"
                f"Location: {self.location}\n"
                f"Prize Pool: {self.prize}\n"
                f"Participants: {self.participants}\n"
                f"Registration Link: {self.registration_link}\n"
                f"{'-'*40}")

def fetch_hackathons(url):
    driver = None
    try:
        # Try Chrome first
        try:
            driver = setup_chrome_driver()
            print("Using Chrome WebDriver")
        except Exception as chrome_error:
            print(f"Chrome WebDriver failed: {chrome_error}")
            try:
                # Try Firefox as fallback
                driver = setup_firefox_driver()
                print("Using Firefox WebDriver as fallback")
            except Exception as firefox_error:
                print(f"Firefox WebDriver also failed: {firefox_error}")
                raise Exception("All WebDriver options failed")
        
        driver.get(url)
        
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "hackathon-tile"))
            )
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            with open('debug.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
        finally:
            if driver:
                driver.quit()
        
        hackathons = []
        for hackathon_div in soup.find_all('div', class_='hackathon-tile'):
            try:
                name_tag = hackathon_div.find('h3')
                name = name_tag.text.strip() if name_tag else "Unknown"

                link_tag = hackathon_div.find('a', class_='tile-anchor', href=True)
                registration_link = link_tag['href'] if link_tag else ""
                if registration_link and not registration_link.startswith('http'):
                    registration_link = "https://devpost.com" + registration_link

                location_tag = hackathon_div.find('div', class_='info')
                location = location_tag.text.strip() if location_tag else "Unknown"

                prize_tag = hackathon_div.find('div', class_='prize-amount')
                prize = prize_tag.text.strip() if prize_tag else "Unknown"

                participants_tag = hackathon_div.find('div', class_='participants')
                participants = participants_tag.text.strip() if participants_tag else "Unknown"

                date_tag = hackathon_div.find('div', class_='submission-period')
                registration_start, registration_end = parse_dates(date_tag.text.strip() if date_tag else "")

                hackathon = Hackathon(name, registration_start, registration_end, location, prize, participants, registration_link)
                hackathons.append(hackathon)
            except Exception as e:
                print(f"Error parsing hackathon: {e}")
                continue

        return hackathons
    except Exception as e:
        print(f"Error fetching hackathons: {e}")
        return []

def setup_chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Bypass version checks
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Try to create driver without service
    try:
        return webdriver.Chrome(options=options)
    except:
        # Fallback to using service
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

def setup_firefox_driver():
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    
    service = FirefoxService(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=options)

def parse_dates(date_text):
    date_pattern = r'(\w{3} \d{1,2}) - (\w{3} \d{1,2}, \d{4})'
    match = re.search(date_pattern, date_text)
    if match:
        try:
            registration_start = datetime.strptime(match.group(1) + " " + match.group(2)[-4:], '%b %d %Y')
            registration_end = datetime.strptime(match.group(2), '%b %d, %Y')
            return registration_start, registration_end
        except ValueError:
            return None, None
    return None, None

def main():
    url = 'https://devpost.com/hackathons'
    hackathons = fetch_hackathons(url)
    for hackathon in hackathons:
        print(hackathon)

if __name__ == '__main__':
    main()
