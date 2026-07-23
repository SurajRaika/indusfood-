import os
import sys
import re
import csv
import json

def unescape_yaml_string(s):
    if not isinstance(s, str):
        return s
    # Strip wrapping double quotes
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    # Replace escaped quotes and backslashes
    return s.replace('\\"', '"').replace('\\\\', '\\')

def load_frontmatter(file_path):
    frontmatter = []
    in_frontmatter = False

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break
            if in_frontmatter:
                frontmatter.append(line)

    yaml_text = "".join(frontmatter)
    try:
        # We can parse with standard json if we formatted some parts,
        # but PyYAML is standard in most environments, or we can use custom regex parsing
        # Let's try custom regex / yaml parsing to be extremely robust without PyYAML dependency
        data = {}
        for line in frontmatter:
            line = line.strip()
            if not line or ":" not in line:
                continue
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()

            # Unwrap string and parse nested lists/dicts if any
            if val.startswith('"') and val.endswith('"'):
                val = unescape_yaml_string(val)
            elif (val.startswith('[') and val.endswith(']')) or (val.startswith('{') and val.endswith('}')):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            elif val.lower() == 'true':
                val = True
            elif val.lower() == 'false':
                val = False
            elif val.isdigit():
                val = int(val)
            elif val == '""':
                val = ""
            data[key] = val
        return data
    except Exception as e:
        print(f"Error parsing frontmatter of {file_path}: {e}", file=sys.stderr)
        return {}

def extract_to_csv(input_dir, output_csv):
    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)

    all_records = []
    all_keys = set()

    print(f"Scanning directory: {input_dir} for exhibitors...")
    for item in sorted(os.listdir(input_dir)):
        item_path = os.path.join(input_dir, item)
        if os.path.isdir(item_path):
            info_file = os.path.join(item_path, "info.md")
            if os.path.isfile(info_file):
                record = load_frontmatter(info_file)
                if record:
                    all_records.append(record)
                    all_keys.update(record.keys())

    if not all_records:
        print("No exhibitor records found to extract.")
        return

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

    print(f"Writing parsed {len(all_records)} exhibitors to {output_csv}...")
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        writer.writeheader()
        for record in all_records:
            formatted_record = {}
            for k in final_headers:
                val = record.get(k, "")
                if isinstance(val, (dict, list)):
                    formatted_record[k] = json.dumps(val, ensure_ascii=False)
                elif val is None:
                    formatted_record[k] = ""
                else:
                    if isinstance(val, str):
                        formatted_record[k] = val.strip()
                    else:
                        formatted_record[k] = val
            writer.writerow(formatted_record)

    print("CSV conversion completed successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_exhibitors.py <exhibitors_directory> [output_csv_filename]")
        print("Example: python3 extract_exhibitors.py exhibitors extracted_exhibitors.csv")
        sys.exit(1)

    input_directory = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else "extracted_exhibitors.csv"

    extract_to_csv(input_directory, output_filename)
