import requests
from bs4 import BeautifulSoup
import sqlite3
from pathlib import Path
import subprocess

# Fetch issuers
def fetch_publisher_codes():
    url = 'https://www.mse.mk/mk/stats/symbolhistory/avk'
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch issuers.")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    dropdown = soup.find('select', {'id': 'Code'})
    publisher_codes = [
        option.get('value') for option in dropdown.find_all('option')
        if option.get('value') and option.get('value').isalpha()
    ] if dropdown else []
    return publisher_codes

# Save issuers to the database
def save_to_database(publishers):
    THIS_FOLDER = Path(__file__).parent.resolve()
    db_path = THIS_FOLDER / "publishers.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS publishers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        publisher_code TEXT UNIQUE)''')
    cursor.execute("DELETE FROM publishers")
    for publisher_code in publishers:
        cursor.execute("INSERT OR IGNORE INTO publishers (publisher_code) VALUES (?)", (publisher_code,))
    conn.commit()
    conn.close()

# Call the next filter
def call_filter2():
    filter2_path = Path(__file__).parent / "filter2.py"  # Ensure the path is correct
    subprocess.run(["python", str(filter2_path)])  # Use str() to convert the path object to string

# Main logic
def main():
    publisher_codes = fetch_publisher_codes()
    if publisher_codes:
        print(f"Found {len(publisher_codes)} issuers.")
        unique_codes = list(set(publisher_codes))
        save_to_database(unique_codes)
        print("Filter1 completed. Calling Filter2...")
        call_filter2()
    else:
        print("No issuers found.")

if __name__ == '__main__':
    main()
