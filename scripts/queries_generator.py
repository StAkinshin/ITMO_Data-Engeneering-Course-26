import os
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CORE_PATH = os.getenv("CORE_PATH")
DATA_PATH = os.path.join(CORE_PATH, "data")
CITIES_PATH = os.path.join(DATA_PATH, "cities.xlsx")
OUTPUT_FILE = os.path.join(DATA_PATH, "queries.json")

cities = pd.read_excel(CITIES_PATH)

queries = []

for city in cities["object_name"].dropna():
    queries.append(f"рабочий дом {city}")

os.makedirs(DATA_PATH, exist_ok = True)

with open(OUTPUT_FILE, "w", encoding = "utf-8") as f:
    json.dump(queries, f, ensure_ascii = False, indent = 4)