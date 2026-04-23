import csv
import json
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UMLS_API_KEY = os.environ.get("UMLS_API_KEY")
if not UMLS_API_KEY:
    raise RuntimeError("Please set the UMLS_API_KEY environment variable before running this script.")

SEARCH_URL = "https://uts-ws.nlm.nih.gov/rest/search/current"
VERSION = "2025AB"

base_path = Path(__file__).resolve().parent
csv_path = base_path / "icd-10-Version-master" / "icd_10_2019_final.csv"

with csv_path.open(newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = [row for _, row in zip(range(50), reader)]

if not rows:
    raise RuntimeError(f"No rows found in {csv_path}")

data = []

for idx, row in enumerate(rows, start=1):
    code = str(row.get("Ids", "")).strip()
    description = str(row.get("Description", "")).strip()
    if not code or not description:
        print(f"Skipping empty row {idx}")
        continue

    msh_def = ""
    nci_def = ""
    medline_def = ""
    print(f"Processing {idx}: {code}")

    params = {
        "string": description,
        "returnIdType": "concept",
        "apiKey": UMLS_API_KEY,
        "pageSize": 1,
        "pageNumber": 1
    }
    response = requests.get(SEARCH_URL, params=params)
    response.raise_for_status()
    result = response.json()

    results = result.get("result", {}).get("results", [])
    if not results:
        print("No UMLS results found for this description.")
    else:
        first_result = results[0]
        cui = first_result.get("ui")
        name = first_result.get("name")
        print("First UMLS CUI:", cui)
        print("First result name:", name)

        if not cui or cui == "NONE":
            print("No valid CUI returned for the first result.")
        else:
            definitions_url = f"https://uts-ws.nlm.nih.gov/rest/content/{VERSION}/CUI/{cui}/definitions"
            def_params = {"apiKey": UMLS_API_KEY}

            try:
                definitions_resp = requests.get(definitions_url, params=def_params)
                definitions_resp.raise_for_status()
                definitions = definitions_resp.json()
            except requests.exceptions.HTTPError as err:
                if definitions_resp.status_code == 404:
                    print("No definitions endpoint found for this CUI.")
                else:
                    raise
            else:
                definitions_dict = {"MSH": [], "NCI": [], "MEDLINEPLUS": []}
                for item in definitions.get("result", []):
                    source = item.get("rootSource")
                    if source in ["MSH", "NCI", "MEDLINEPLUS"]:
                        text = item.get("value") or item.get("definition") or item.get("name")
                        if text:
                            if source == "MEDLINEPLUS":
                                text = BeautifulSoup(text, 'html.parser').get_text()
                            definitions_dict[source].append(text)

                msh_def = "; ".join(definitions_dict["MSH"])
                nci_def = "; ".join(definitions_dict["NCI"])
                medline_def = "; ".join(definitions_dict["MEDLINEPLUS"])

    data.append({
        "ICD10_code": code,
        "name": description,
        "MSH_Definition": msh_def,
        "NCI_Definition": nci_def,
        "MEDLINEPLUS_Definition": medline_def
    })

# Write to CSV
csv_output_path = base_path / "umls_definitions.csv"
with csv_output_path.open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=["ICD10_code", "name", "MSH_Definition", "NCI_Definition", "MEDLINEPLUS_Definition"])
    writer.writeheader()
    writer.writerows(data)

# Write to JSON
json_output_path = base_path / "umls_definitions.json"
with json_output_path.open('w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Data written to umls_definitions.csv and umls_definitions.json")

