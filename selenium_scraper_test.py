import argparse
import os
import time
import glob
import random
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote

def setup_driver():
    """Setup and configure the Chrome WebDriver with additional stability options."""
    download_dir = os.path.abspath(os.path.join(os.getcwd(), 'downloads'))
    os.makedirs(download_dir, exist_ok=True)
    download_dir_win = os.path.normpath(download_dir)
    
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    prefs = {
        "download.default_directory": download_dir_win,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
        "profile.default_content_settings.popups": 0
    }
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    
    return driver, download_dir

def wait_for_download(download_dir, timeout=30):
    """Wait for CSV file to appear in download directory."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = glob.glob(os.path.join(download_dir, '*.csv'))
        if files:
            latest_file = max(files, key=os.path.getctime)
            if os.path.basename(latest_file).lower() != 'sample.csv' and os.path.getsize(latest_file) > 0:
                # Wait a bit to ensure file is fully written
                time.sleep(2)
                return latest_file
        time.sleep(0.5)
    return None

def wait_for_page_load(driver, wait):
    """Wait for key elements to load on the page."""
    try:
        # Wait for page to be fully loaded
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        # Wait for any loading spinners to disappear
        wait.until_not(EC.presence_of_element_located((By.CSS_SELECTOR, '.loading-spinner')))
        
        # Wait for the main content container
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 
            'div.fe-atoms-generic-content-container, div.fe-line-chart-content-container')))
        
        return True
    except (TimeoutException, WebDriverException) as e:
        print(f"Error waiting for page load: {str(e)}")
        return False

def scrape_batch_trends(keywords, start_date, end_date, max_retries=3):
    """Scrape Google Trends data for multiple keywords with retries."""
    for attempt in range(max_retries):
        driver = None
        try:
            driver, download_dir = setup_driver()
            wait = WebDriverWait(driver, 30)
            
            # Construct URL with multiple keywords
            encoded_keywords = [quote(keyword) for keyword in keywords]
            query_string = '%2C'.join(encoded_keywords)
            base_url = "https://trends.google.com/trends/explore"
            url = f"{base_url}?date={start_date}%20{end_date}&q={query_string}&hl=en"  # Force English
            
            print(f"\nAttempt {attempt + 1}: Accessing Google Trends for keywords: {', '.join(keywords)}")
            
            # Load the page
            driver.get(url)
            if not wait_for_page_load(driver, wait):
                raise Exception("Page failed to load completely")
            
            # Handle cookie consent
            try:
                consent_buttons = driver.find_elements(By.XPATH, 
                    "//button[contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Agree')]")
                if consent_buttons:
                    driver.execute_script("arguments[0].click();", consent_buttons[0])
                    time.sleep(2)
            except Exception as e:
                print(f"Cookie consent handling failed (non-critical): {str(e)}")
            
            # Wait for data to load
            time.sleep(5)
            
            # Find and click download button with multiple attempts
            download_button = None
            for selector in [
                "button.widget-actions-item.export",
                "button.export-button",
                "button[title='Export data']",
                "button.widget-actions-item"
            ]:
                try:
                    download_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if download_button:
                        break
                except:
                    continue
            
            if not download_button:
                raise Exception("Download button not found")
            
            # Try multiple click methods
            click_success = False
            try:
                # Scroll to button
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                time.sleep(2)
                
                # Try different click methods
                try:
                    download_button.click()
                    click_success = True
                except:
                    try:
                        driver.execute_script("arguments[0].click();", download_button)
                        click_success = True
                    except:
                        actions = webdriver.ActionChains(driver)
                        actions.move_to_element(download_button).click().perform()
                        click_success = True
            except Exception as e:
                print(f"Click attempt failed: {str(e)}")
            
            if not click_success:
                raise Exception("Failed to click download button")
            
            # Wait for CSV download
            csv_file = wait_for_download(download_dir, timeout=45)
            if not csv_file:
                raise Exception("CSV file was not downloaded")
            
            # Read and return content
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            # Clean up downloaded file
            if os.path.exists(csv_file):
                os.remove(csv_file)
            
            print(f"Successfully retrieved data on attempt {attempt + 1}")
            return content
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                delay = random.uniform(10, 20)
                print(f"Waiting {delay:.1f} seconds before retry...")
                time.sleep(delay)
            else:
                print("All attempts failed")
                return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

def extract_batch_trend_data(csv_content, keywords):
    """Extract trend data for multiple keywords from CSV content."""
    if not csv_content:
        return []
    
    results = []
    try:
        lines = csv_content.strip().split('\n')
        
        # Find data section
        data_start_idx = -1
        for i, line in enumerate(lines):
            if 'Interest over time' in line:
                data_start_idx = i
                break
        
        if data_start_idx == -1:
            print("Could not find 'Interest over time' section in CSV")
            return []
        
        # Get headers (date + keywords)
        headers = [h.strip('"').strip() for h in lines[data_start_idx + 1].strip().split(',')]
        if len(headers) < 2:
            print("Invalid header format in CSV")
            return []
        
        # Process data rows
        for line in lines[data_start_idx + 2:]:
            line = line.strip()
            if not line or line.startswith('Category:'):
                break
                
            values = [v.strip('"').strip() for v in line.split(',')]
            if len(values) < 2:
                continue
                
            date = values[0]
            
            # Add data point for each keyword
            for i, interest in enumerate(values[1:], 1):
                if i < len(headers):
                    keyword = headers[i]
                    interest_val = '0' if interest == '<1' else interest
                    results.append([date, interest_val, keyword])
        
        return results
        
    except Exception as e:
        print(f"Error extracting batch trend data: {str(e)}")
        return []

def process_keywords(keywords, start_date, end_date, output_file, batch_size=5):
    """Process keywords in batches and save results."""
    results = []
    
    # Process keywords in batches
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{(len(keywords) + batch_size - 1)//batch_size}")
        print(f"Keywords: {', '.join(batch)}")
        
        content = scrape_batch_trends(batch, start_date, end_date)
        if content:
            batch_results = extract_batch_trend_data(content, batch)
            if batch_results:
                results.extend(batch_results)
                print(f"Successfully processed {len(set(row[2] for row in batch_results))} keywords")
            else:
                print("Failed to extract trend data for batch")
        else:
            print("Failed to get data for batch")
        
        # Add delay between batches
        if i + batch_size < len(keywords):
            delay = random.uniform(30, 45)
            print(f"Waiting {delay:.1f} seconds before next batch...")
            time.sleep(delay)
    
    # Save results
    if results:
        file_exists = os.path.exists(output_file)
        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Date', 'Interest', 'Keyword'])
            writer.writerows(results)
        
        print(f"\nSaved data for {len(set(row[2] for row in results))} keywords to {output_file}")
    
    return [row[2] for row in results]

def main():
    parser = argparse.ArgumentParser(description='Batch scrape Google Trends data for movies.')
    parser.add_argument('--csv', type=str, default='sample.csv',
                        help='Path to CSV file with movie data')
    parser.add_argument('--batch', type=int, default=5,
                        help='Number of keywords to process in each batch')
    parser.add_argument('--output', type=str, default='movie_trends.csv',
                        help='Path to output CSV file')
    
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, args.csv)
    output_file = os.path.join(script_dir, args.output)
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return
    
    # Set date range
    start_date = "2006-01-01"
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Load keywords
    with open(csv_path, 'r') as f:
        keywords = [row['title'] for row in csv.DictReader(f)]
    
    # Get already processed keywords
    processed = set()
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            processed = {row[2] for row in reader}
    
    # Filter unprocessed keywords
    keywords_to_process = [k for k in keywords if k not in processed]
    
    if not keywords_to_process:
        print("All keywords have been processed.")
        return
    
    print(f"Processing {len(keywords_to_process)} keywords in batches of {args.batch}")
    print(f"Date range: {start_date} to {end_date}")
    process_keywords(keywords_to_process, start_date, end_date, output_file, args.batch)
    print("\nAll batches completed!")

if __name__ == '__main__':
    main()