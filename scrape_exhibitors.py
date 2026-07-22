import urllib.request
import json
import csv
import sys
import time

LIST_URL = "https://ahmedabad.indusfood.co.in/api/exhibitor-list.php"
DETAIL_URL = "https://ahmedabad.indusfood.co.in/api/exhibitor-detail.php"

def make_post_request(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST"
    )
    attempts = 3
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"Error requesting {url} (attempt {attempt+1}/{attempts}): {e}", file=sys.stderr)
            if attempt < attempts - 1:
                time.sleep(2)
            else:
                raise e

def scrape_all():
    print("Starting scraping exhibitors list...")
    limit = 100
    offset = 0
    all_exhibitor_briefs = []

    # First, fetch all the briefs from exhibitor-list.php
    while True:
        payload = {"limit": limit, "offset": offset}
        print(f"Fetching list starting from offset {offset} with limit {limit}...")
        res = make_post_request(LIST_URL, payload)
        if not res or not res.get("success"):
            print("Failed to get response or success was false.", file=sys.stderr)
            break

        data_block = res.get("data", {})
        exhibitors = data_block.get("data", [])
        if not exhibitors:
            break

        all_exhibitor_briefs.extend(exhibitors)
        print(f"Retrieved {len(exhibitors)} exhibitors. Total so far: {len(all_exhibitor_briefs)}")

        # Check total records to stop
        total_records = data_block.get("totalRecords", 0)
        if len(all_exhibitor_briefs) >= total_records or len(exhibitors) < limit:
            print(f"All {total_records} records collected (briefs list count: {len(all_exhibitor_briefs)}).")
            break

        offset += limit
        time.sleep(1)

    print(f"Total briefs collected: {len(all_exhibitor_briefs)}")

    all_details = []

    # Next, retrieve detailed info for each exhibitor using their ID
    for idx, brief in enumerate(all_exhibitor_briefs):
        ex_id = brief.get("id")
        comp_name = brief.get("company_name", "Unknown Company")
        print(f"[{idx+1}/{len(all_exhibitor_briefs)}] Fetching details for: {comp_name} (ID: {ex_id})...")

        try:
            detail_res = make_post_request(DETAIL_URL, {"id": ex_id})
            if detail_res and detail_res.get("success"):
                detail_data = detail_res.get("data", {})
                # Merge brief and detail fields. Details often contain more info.
                # If there are overlaps, detailed info takes precedence.
                merged = {**brief, **detail_data}
                # Keep original ID as well
                merged["id"] = ex_id
                all_details.append(merged)
            else:
                print(f"Warning: failed to get details for {comp_name}. Using brief info only.", file=sys.stderr)
                all_details.append(brief)
        except Exception as e:
            print(f"Error fetching details for {comp_name}: {e}. Saving brief info.", file=sys.stderr)
            all_details.append(brief)

        time.sleep(0.1) # courteous scraping speed but not too slow

    # Determine headers dynamically from all keys found across all records to not lose any data
    all_keys = set()
    for record in all_details:
        all_keys.update(record.keys())

    # Order headers reasonably
    priority_headers = [
        "id", "company_name", "type_of_company", "contact_person", "nature_of_company",
        "industry", "product_zone", "products", "product_list",
        "stall_no", "hall_no", "website", "company_address", "city_name", "state", "country", "pin_code",
        "pan_no", "whatsapp_no", "facebook_link", "linkedin_link", "twitter_link", "youtube_link", "instagram_link",
        "annual_export", "majorly_looking_for", "company_profile", "company_logo", "brochure", "certifications", "certifications_list"
    ]

    headers = [h for h in priority_headers if h in all_keys]
    remaining_headers = sorted(list(all_keys - set(headers)))
    final_headers = headers + remaining_headers

    output_filename = "exhibitors.csv"
    print(f"Writing {len(all_details)} exhibitors to {output_filename}...")

    with open(output_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        writer.writeheader()
        for record in all_details:
            # Clean and format nested dicts or lists as json strings for readability in CSV
            formatted_record = {}
            for k in final_headers:
                val = record.get(k, "")
                if isinstance(val, (dict, list)):
                    formatted_record[k] = json.dumps(val, ensure_ascii=False)
                elif val is None:
                    formatted_record[k] = ""
                else:
                    # Clean trailing spaces/newlines
                    if isinstance(val, str):
                        formatted_record[k] = val.strip()
                    else:
                        formatted_record[k] = val
            writer.writerow(formatted_record)

    print("Scraping completed successfully!")

if __name__ == "__main__":
    scrape_all()
