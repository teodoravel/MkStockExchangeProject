import requests
import sqlite3
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

THIS_FOLDER = Path(__file__).parent.resolve()
DB_PATH = THIS_FOLDER / "stock_data.db"
LAST_DATES_PATH = THIS_FOLDER / "last_dates.json"
BASE_URL = 'https://www.mse.mk/mk/stats/symbolhistory/'

# Fetch the last data date for an issuer
def get_last_data_date(publisher_code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS stock_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        publisher_code TEXT,
                        date TEXT,
                        price TEXT,
                        max TEXT,
                        min TEXT,
                        avg TEXT,
                        percent_change TEXT,
                        quantity TEXT,
                        best_turnover TEXT,
                        total_turnover TEXT,
                        UNIQUE(publisher_code, date) ON CONFLICT REPLACE)''')
    cursor.execute("SELECT MAX(date) FROM stock_data WHERE publisher_code = ?", (publisher_code,))
    last_date = cursor.fetchone()[0]
    conn.close()
    return last_date if last_date else None

# Fetch stock data from the website
def fetch_stock_data(publisher_code, from_date, to_date):
    params = {'FromDate': from_date, 'ToDate': to_date, 'Code': publisher_code}
    response = requests.get(BASE_URL + publisher_code, params=params)
    return response.text if response.status_code == 200 else None

# Parse stock data
def parse_stock_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'id': 'resultsTable'})
    data = []
    if table:
        rows = table.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            data.append({
                'Date': cols[0].text.strip(),
                'Price': cols[1].text.strip(),
                'Max': cols[2].text.strip(),
                'Min': cols[3].text.strip(),
                'Avg': cols[4].text.strip(),
                'Percent Change': cols[5].text.strip(),
                'Quantity': cols[6].text.strip(),
                'Best Turnover': cols[7].text.strip(),
                'Total Turnover': cols[8].text.strip()
            })
    return data

# Save stock data to the database
def save_to_database(publisher_code, data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for record in data:
        cursor.execute('''INSERT OR REPLACE INTO stock_data (
                            publisher_code, date, price, max, min, avg, percent_change, quantity, best_turnover, total_turnover)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (publisher_code, record['Date'], record['Price'], record['Max'], record['Min'],
                        record['Avg'], record['Percent Change'], record['Quantity'],
                        record['Best Turnover'], record['Total Turnover']))
    conn.commit()
    conn.close()

# Process a single publisher
def process_publisher(publisher_code):
    last_date = get_last_data_date(publisher_code)
    if not last_date:
        print(f"Issuer {publisher_code} has no data. Fetching data for the last 10 years.")
        from_date = datetime.now() - timedelta(days=365 * 10)
    else:
        print(f"Issuer {publisher_code} has data up to {last_date}. Fetching missing data.")
        from_date = datetime.strptime(last_date, '%d.%m.%Y') + timedelta(days=1)
    to_date = datetime.now()
    while from_date < to_date:
        end_date = min(from_date + timedelta(days=365), to_date)
        html = fetch_stock_data(publisher_code, from_date.strftime('%d.%m.%Y'), end_date.strftime('%d.%m.%Y'))
        if html:
            data = parse_stock_table(html)
            if data:
                save_to_database(publisher_code, data)
        from_date = end_date + timedelta(days=1)
    return (publisher_code, datetime.now().strftime('%d.%m.%Y'))

# Process all issuers using multithreading
def process_publishers(publisher_codes):
    last_dates = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_publisher = {executor.submit(process_publisher, code): code for code in publisher_codes}
        for future in as_completed(future_to_publisher):
            publisher_code = future_to_publisher[future]
            try:
                result = future.result()
                last_dates[result[0]] = result[1]
            except Exception as exc:
                print(f"{publisher_code} generated an exception: {exc}")
    # Write last_dates to json file
    with open(LAST_DATES_PATH, 'w') as json_file:
        json.dump(last_dates, json_file)

# Call the next filter
def call_filter3():
    subprocess.run(["python", str(THIS_FOLDER / "filter3.py")])

# Main logic
def main():
    with sqlite3.connect(THIS_FOLDER / "publishers.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT publisher_code FROM publishers")
        publisher_codes = [row[0] for row in cursor.fetchall()]
    if publisher_codes:
        process_publishers(publisher_codes)
        print("Filter2 completed. Calling Filter3...")
        call_filter3()
    else:
        print("No issuers found.")

if __name__ == '__main__':
    main()
