import urllib.request
import json
import csv
import sys
import time
import os
import re

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

def sanitize_filename(name):
    # Keep alphanumeric characters, spaces, hyphens, and underscores, then replace spaces/hyphens/etc with underscores
    s = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name)
    s = re.sub(r'[\s\-]+', '_', s)
    return s.strip('_').upper()

def escape_yaml_string(s):
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    # Escape backslashes and double quotes, and wrap in double quotes
    s_escaped = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
    return f'"{s_escaped}"'

def format_yaml_value(val):
    if val is None:
        return '""'
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, bool):
        return 'true' if val else 'false'
    if isinstance(val, (int, float)):
        return str(val)
    return escape_yaml_string(val)

def generate_markdown(record):
    # Generate structured YAML frontmatter for easy programmatic extraction
    yaml_lines = ["---"]
    for k, v in sorted(record.items()):
        yaml_lines.append(f"{k}: {format_yaml_value(v)}")
    yaml_lines.append("---")
    yaml_frontmatter = "\n".join(yaml_lines)

    # Human-readable markdown presentation
    company_name = record.get("company_name", "Unknown Exhibitor")
    industry = record.get("industry", "N/A")
    stall = record.get("stall_no", "N/A")
    hall = record.get("hall_no", "N/A")
    country = record.get("country", "N/A")
    website = record.get("website", "N/A")
    contact = record.get("contact_person", "N/A")
    nature = record.get("nature_of_company", "N/A")
    profile = record.get("company_profile", "No profile provided.")
    address = record.get("company_address", "N/A")
    whatsapp = record.get("whatsapp_no", "N/A")

    md_body = f"""
# {company_name}

## Overview
- **Industry:** {industry}
- **Country:** {country}
- **Stall:** {stall} (Hall {hall})
- **Website:** [{website}]({website}) if {website} != "N/A" else "N/A"
- **Contact Person:** {contact}
- **Nature of Company:** {nature}
- **WhatsApp:** {whatsapp}

## Company Profile
{profile}

## Contact Details
- **Address:** {address}
- **City:** {record.get("city_name", "N/A")}
- **State:** {record.get("state", "N/A")}
- **Pincode:** {record.get("pin_code", "N/A")}

### Social Links
- **Facebook:** {record.get("facebook_link", "N/A")}
- **LinkedIn:** {record.get("linkedin_link", "N/A")}
- **Twitter:** {record.get("twitter_link", "N/A")}
- **Instagram:** {record.get("instagram_link", "N/A")}
- **YouTube:** {record.get("youtube_link", "N/A")}
"""
    # Quick string formatting cleanup for Website link
    if website == "N/A":
        md_body = md_body.replace('- **Website:** [N/A](N/A) if N/A != "N/A" else "N/A"', '- **Website:** N/A')
    else:
        md_body = md_body.replace(f'- **Website:** [{website}]({website}) if {website} != "N/A" else "N/A"', f'- **Website:** [{website}]({website})')

    return f"{yaml_frontmatter}\n{md_body}"

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

        time.sleep(0.05) # courteous scraping speed but not too slow

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

    # 1. Write to CSV
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

    # 2. Write Markdown Folders for each exhibitor
    base_dir = "exhibitors"
    os.makedirs(base_dir, exist_ok=True)
    print(f"Creating individual folders and info.md files under directory: {base_dir}/")

    for record in all_details:
        comp_name = record.get("company_name", "Unknown_Company")
        folder_name = sanitize_filename(comp_name)
        # Ensure name isn't completely empty
        if not folder_name:
            folder_name = "UNKNOWN_COMPANY_" + record.get("id", "")[:10]

        ex_dir = os.path.join(base_dir, folder_name)
        os.makedirs(ex_dir, exist_ok=True)

        md_content = generate_markdown(record)
        md_filepath = os.path.join(ex_dir, "info.md")

        with open(md_filepath, "w", encoding="utf-8") as f:
            f.write(md_content)

    print("Scraping and file creation completed successfully!")

if __name__ == "__main__":
    scrape_all()
