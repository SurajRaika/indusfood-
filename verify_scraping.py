import urllib.request
import json
import os
import sys

LIST_URL = "https://ahmedabad.indusfood.co.in/api/exhibitor-list.php"

def get_server_total():
    req = urllib.request.Request(
        LIST_URL,
        data=json.dumps({"limit": 1, "offset": 0}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data and data.get("success"):
                return data["data"].get("totalRecords", 0)
    except Exception as e:
        print(f"Error querying server: {e}", file=sys.stderr)
    return None

def verify():
    print("==========================================")
    print("        SCARPER VERIFICATION REPORT       ")
    print("==========================================")

    server_total = get_server_total()
    if server_total is None:
        print("Failed to contact the server to retrieve total record count.", file=sys.stderr)
        sys.exit(1)

    print(f"Total exhibitors reported by Server API: {server_total}")

    # Check exhibitors folders
    folders_count = 0
    missing_info_files = 0
    base_dir = "exhibitors"

    if os.path.exists(base_dir) and os.path.isdir(base_dir):
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                folders_count += 1
                info_path = os.path.join(item_path, "info.md")
                if not os.path.exists(info_path):
                    missing_info_files += 1
    else:
        print(f"Error: Directory '{base_dir}' does not exist locally.", file=sys.stderr)
        sys.exit(1)

    print(f"Total local exhibitor folders found   : {folders_count}")
    print(f"Folders missing 'info.md' file        : {missing_info_files}")

    # Verify exact match
    if folders_count == server_total and missing_info_files == 0:
        print("\n[SUCCESS] Verification Passed!")
        print("-> 100% of all exhibitors on the server have been successfully scraped.")
        print("-> Every single exhibitor has their dedicated folder and 'info.md' file.")
        print("==========================================")
        sys.exit(0)
    else:
        print("\n[FAILURE] Verification Failed!")
        if folders_count != server_total:
            print(f"-> Count mismatch: Server has {server_total}, but local has {folders_count}.")
        if missing_info_files > 0:
            print(f"-> Error: {missing_info_files} folders are missing 'info.md' files.")
        print("==========================================")
        sys.exit(1)

if __name__ == "__main__":
    verify()
