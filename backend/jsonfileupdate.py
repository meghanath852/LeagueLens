from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time
import requests
from bs4 import BeautifulSoup
import json


def connect(match_id):
  options = Options()
  options.add_argument("--headless")
  options.add_argument("--disable-gpu")
  options.add_argument("--no-sandbox")
  options.add_argument("window-size=1920,1080")
  options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

  driver = webdriver.Chrome(options=options)
  json_url = "https://www.espncricinfo.com/matches/engine/match/{0}.json".format(match_id)
  driver.get(json_url)
  time.sleep(1)
  raw_json = driver.find_element("tag name", "pre").text
  driver.quit()
  data = json.loads(raw_json)
  return data

def update_live_matches():
  print(f"Running update at {time.strftime('%Y-%m-%d %H:%M:%S')}")
  response = requests.request(url="http://static.cricinfo.com/rss/livescores.xml", method="GET")
  xml = BeautifulSoup(response.text, 'xml')
  print(xml)
  
  live_list_id = []
  try:
    xml = BeautifulSoup(response.text, 'xml')
    matches = [x.link.text.split(".html")[0].split('/')[6] for x in xml.find_all('item')]
    for j in matches:
      data = connect(j)
      if data['series'][0]['series_short_name'] == 'IPL' and data['match']['current_summary'].split()[-2:] != ['Match','over']:
        live_list_id.append(j)
    print(f"Live matches found: {live_list_id}")
  except Exception as e:
    print(f"Error fetching matches: {e}")
    return

  try:
    with open("data_live.json", "r") as file:
      data = json.load(file)
  except (FileNotFoundError, json.JSONDecodeError):
    print("Creating new data_live.json file")
    data = {}

  keys_to_remove = [i for i in data.keys() if i not in live_list_id]

  for key in keys_to_remove:
    data.pop(key)

  for j in live_list_id:
    data[j] = connect(j)
    
  with open("data_live.json", "w") as file:
    json.dump(data, file)
  
  print(f"Update completed. Next update in {UPDATE_INTERVAL} seconds.\n")

# Main execution loop
UPDATE_INTERVAL = 2

if __name__ == "__main__":
  print("Starting continuous update script. Press Ctrl+C to stop.")
  try:
    while True:
      update_live_matches()
      time.sleep(UPDATE_INTERVAL)
  except KeyboardInterrupt:
    print("\nScript stopped by user. Exiting...")
  except Exception as e:
    print(f"\nUnexpected error occurred: {e}")