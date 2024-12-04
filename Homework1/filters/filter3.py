import sqlite3
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Define paths for the database and JSON file with last dates
THIS_FOLDER = Path(__file__).parent.resolve()
DB_PATH = THIS_FOLDER / "stock_data.db"
LAST_DATES_PATH = THIS_FOLDER / "last_dates.json"
BASE_URL = 'https://www.mse.mk/mk/stats/symbolhistory/'

# Format prices
def format_price(value):
    try:
        return "{:,.2f}".format(float(value.replace(',', ''))).replace(',', ' ')
    except ValueError:
        return value

# Function to ensure date format consistency
def format_date(date_str):
    try:
        return datetime.strptime(date_str, '%d.%m.%Y').strftime('%d.%m.%Y')
    except ValueError:
        return date_str

# Fetch stock data from MSE
def fetch_stock_data(publisher_code, from_date, to_date):
    params = {
        'FromDate': from_date,
        'ToDate': to_date,
        'Code': publisher_code
    }
    response = requests.get(BASE_URL + publisher_code, params=params)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Error fetching data for {publisher_code}. Status code: {response.status_code}")
        return None

# Parse stock data table from HTML
def parse_stock_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'id': 'resultsTable'})
    if not table:
        print("Table not found!")
        return []
    rows = table.find_all('tr')
    data = []
    for row in rows[1:]:  # Skip header row
        cols = row.find_all('td')
        if len(cols) > 1:
            data.append({
                'Date': format_date(cols[0].text.strip()),
                'Price': format_price(cols[1].text.strip()),
                'Max': format_price(cols[2].text.strip()),
                'Min': format_price(cols[3].text.strip()),
                'Avg': format_price(cols[4].text.strip()),
                'Percent Change': cols[5].text.strip(),
                'Quantity': cols[6].text.strip(),
                'Best Turnover': format_price(cols[7].text.strip()),
                'Total Turnover': format_price(cols[8].text.strip())
            })
    return data

# Function to save new stock data to the db if it has a newer date
def save_new_data(publisher_code, data, last_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_data_added = False
    for record in data:
        record_date = record['Date']
        # Only add records with dates newer than `last_date`
        if record_date > last_date:
            cursor.execute('''INSERT OR REPLACE INTO stock_data (publisher_code, date, price, max, min, avg, percent_change, quantity, best_turnover, total_turnover)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                publisher_code,
                record_date,
                record['Price'],
                record['Max'],
                record['Min'],
                record['Avg'],
                record['Percent Change'],
                record['Quantity'],
                record['Best Turnover'],
                record['Total Turnover']
            ))
            print(f"Added record for {publisher_code} on {record_date}")
            new_data_added = True
    conn.commit()
    conn.close()
    return new_data_added

# Function to fetch and format missing data for a single publisher
def process_publisher(publisher_code, from_date):
    try:
        print(f"Fetching new data for {publisher_code} from {from_date} to today.")
        from_datetime = datetime.strptime(from_date, '%d.%m.%Y') + timedelta(days=1)
        to_datetime = datetime.now()
        while from_datetime < to_datetime:
            end_datetime = min(from_datetime + timedelta(days=365), to_datetime)
            html = fetch_stock_data(publisher_code, from_datetime.strftime('%d.%m.%Y'), end_datetime.strftime('%d.%m.%Y'))
            if html:
                data = parse_stock_table(html)
                if data:
                    save_new_data(publisher_code, data, from_date)
            from_datetime = end_datetime + timedelta(days=1)
    except Exception as e:
        print(f"Error processing {publisher_code}: {e}")

# Function to fetch and format missing data for each publisher using multithreading
def fetch_and_format_missing_data():
    # Load the last dates for each publisher from JSON
    try:
        with open(LAST_DATES_PATH, 'r') as json_file:
            last_dates = json.load(json_file)
    except FileNotFoundError:
        print("No last_dates.json file found.")
        return
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for publisher_code, from_date in last_dates.items():
            futures.append(executor.submit(process_publisher, publisher_code, from_date))
        for future in as_completed(futures):
            pass  # We could handle exceptions here if needed

# Main function
def main():
    fetch_and_format_missing_data()

if __name__ == '__main__':
    main()
