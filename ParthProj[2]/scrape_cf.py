import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time
import random
from urllib3.exceptions import InsecureRequestWarning
import warnings
import cloudscraper

# Suppress SSL warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
]

class Contest:
    def __init__(self, name, start_date, end_date, registration_start, registration_end, location, prize, participants, registration_link, duration):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.registration_start = registration_start
        self.registration_end = registration_end
        self.location = location
        self.prize = prize
        self.participants = participants
        self.registration_link = registration_link
        self.duration = duration

    def __str__(self):
        return (f"Contest Name: {self.name}\n"
                f"Start Date: {self.start_date}\n"
                f"End Date: {self.end_date}\n"
                f"Registration Start: {self.registration_start}\n"
                f"Registration End: {self.registration_end}\n"
                f"Location: {self.location}\n"
                f"Prize Pool: {self.prize}\n"
                f"Participants: {self.participants}\n"
                f"Registration Link: {self.registration_link}\n"
                f"Duration: {self.duration}\n"
                f"{'-'*40}")

def clean_contest_name(name):
    # Remove extra whitespace and text like "Enter »" and "Virtual participation »"
    name = re.sub(r'\s+', ' ', name)  # Replace multiple spaces with single space
    name = re.sub(r'\s*»\s*', '', name)  # Remove » and surrounding spaces
    name = re.sub(r'\s*Enter\s*', '', name)  # Remove "Enter" and surrounding spaces
    name = re.sub(r'\s*Virtual participation\s*', '', name)  # Remove "Virtual participation" and surrounding spaces
    return name.strip()

def parse_time(time_cell):
    # Try to find the time span using the correct class name
    time_span = time_cell.find('span', class_='format-date') # Use 'format-date'
    
    if not time_span:
        # If still not found, maybe try 'format-time' as a fallback?
        time_span = time_cell.find('span', class_='format-time') 
        if not time_span:
            # print(f"DEBUG: Neither 'format-date' nor 'format-time' span found in cell: {time_cell.prettify()}") 
            return None

    time_text = time_span.text.strip()
    if not time_text:
        return None

    start_time = None
    supported_formats = ['%b/%d/%Y %H:%M', '%B/%d/%Y %H:%M']
    
    for fmt in supported_formats:
        try:
            start_time = datetime.strptime(time_text, fmt)
            break # Exit loop if parsing succeeds
        except ValueError:
            start_time = None # Reset start_time if format failed

    if start_time is None:
        return None
    
    return start_time

def parse_duration(duration_text):
    # Duration is in format "02:15" (hours:minutes)
    try:
        hours, minutes = map(int, duration_text.split(':'))
        return timedelta(hours=hours, minutes=minutes)
    except:
        return timedelta()

def parse_registration_status(status):
    # Convert status codes to readable text
    if status.startswith('x'):
        return f"Registered ({status[1:]} participants)"
    elif status == "Registration closed":
        return "Registration Closed"
    elif status == "Registration open":
        return "Open for Registration"
    elif "Before registration" in status:
        return "Registration Not Started"
    else:
        return status

def fetch_contests(url):
    max_retries = 3
    current_retry = 0
    
    while current_retry < max_retries:
        try:
            # Create a cloudscraper instance
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )

            # Randomly select a user agent
            user_agent = random.choice(USER_AGENTS)
            scraper.headers.update({'User-Agent': user_agent})

            # Add random delay between 2-5 seconds
            time.sleep(random.uniform(2, 5))

            # Make the request using cloudscraper
            print("Fetching contests page with cloudscraper...")
            response = scraper.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')

            with open('debug_cf.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())

            contests = []
            
            # Find all divs that might contain contest tables (look for "th" elements)
            divs_with_tables = soup.find_all('div', style=lambda x: x and 'background-color: white' in x)
            
            # Find the first div that has "Name" and "Start" in th tags - this is the current contests table
            current_contests_div = None
            for div in divs_with_tables:
                th_elements = div.find_all('th')
                header_texts = [th.get_text(strip=True) for th in th_elements]
                
                if 'Name' in header_texts and 'Start' in header_texts:
                    current_contests_div = div
                    # Take the first matching div only (current contests)
                    break
            
            if not current_contests_div:
                print("Could not find current/upcoming contests div")
                return []

            # Get all the rows (tr tags) in this div
            contest_rows = current_contests_div.find_all('tr')
            # Skip the header row
            contest_rows = contest_rows[1:]
            
            print(f"Found {len(contest_rows)} current/upcoming contests")

            for row in contest_rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        continue

                    name_cell = cells[0]
                    name = clean_contest_name(name_cell.text)
                    link = name_cell.find('a')
                    registration_link = f"https://codeforces.com{link['href']}" if link else ""

                    time_cell = cells[2]
                    start_date = parse_time(time_cell)

                    duration = parse_duration(cells[3].text.strip())
                    end_date = start_date + duration if start_date else None

                    state_cell = cells[4]
                    before_start_text = state_cell.text.strip()
                    days_before_start_match = re.search(r'(\d+) days', before_start_text)
                    days_before_start = int(days_before_start_match.group(1)) if days_before_start_match else 0

                    # Registration status is in the 6th cell
                    reg_status_cell = cells[5]
                    reg_status_text = reg_status_cell.text.strip()
                    
                    # Initialize registration times
                    registration_start = None
                    registration_end = None
                    
                    # For contests where registration is open
                    if "Register" in reg_status_text:
                        # Registration is currently open, so it started in the past
                        # Set it to a clean midnight time 3 days before start
                        if start_date:
                            registration_start = (start_date - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
                        else:
                            registration_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=3)
                        # Registration ends when the contest starts
                        registration_end = start_date
                    
                    # For contests where registration hasn't started yet
                    elif "Before registration" in reg_status_text:
                        # Check for days format
                        days_before_reg_match = re.search(r'(\d+) days', reg_status_text)
                        
                        # Check for weeks format
                        weeks_before_reg_match = re.search(r'(\d+) weeks', reg_status_text)
                        
                        days_before_reg = 0
                        
                        if days_before_reg_match:
                            days_before_reg = int(days_before_reg_match.group(1))
                        elif weeks_before_reg_match:
                            # Convert weeks to days (1 week = 7 days)
                            weeks = int(weeks_before_reg_match.group(1))
                            days_before_reg = weeks * 7
                        
                        if days_before_reg > 0:
                            # Calculate when registration will start (from today)
                            registration_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_before_reg)
                            # Registration typically ends when the contest starts
                            registration_end = start_date
                    else:
                        # Default case: assume registration starts 7 days before contest
                        if start_date:
                            registration_start = start_date - timedelta(days=7)
                            registration_end = start_date
                    
                    # Extract participant count if available
                    participants = "Unknown"
                    if "x" in reg_status_text:
                        try:
                            participants = reg_status_text.split("x")[-1].split()[0]
                        except:
                            pass

                    contest = Contest(
                        name=name,
                        start_date=start_date,
                        end_date=end_date,
                        registration_start=registration_start,
                        registration_end=registration_end,
                        location="Online",
                        prize="None",
                        participants=participants,
                        registration_link=registration_link,
                        duration=str(duration)
                    )
                    contests.append(contest)
                except Exception as e:
                    print(f"Error parsing contest: {e}")
                    continue

            return contests
        except Exception as e:
            current_retry += 1
            print(f"Attempt {current_retry} failed: {e}")
            if current_retry < max_retries:
                print(f"Retrying in {current_retry * 2} seconds...")
                time.sleep(current_retry * 2)
            else:
                print("All retry attempts failed")
                return []

    return []

def main():
    url = 'https://codeforces.com/contests'
    contests = fetch_contests(url)
    for contest in contests:
        print(contest)

if __name__ == '__main__':
    main() 