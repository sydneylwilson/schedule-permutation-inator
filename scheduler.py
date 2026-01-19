import argparse
import csv
from datetime import datetime
from playwright.sync_api import sync_playwright

def write_csv(output_path, header, rows):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(
        description="Export When2Meet availability as CSV"
    )
    parser.add_argument("url", help="When2Meet event URL")
    parser.add_argument(
        "-o", "--output",
        default="when2meet_export.csv",
        help="Output CSV filename"
    )

    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(args.url, wait_until="domcontentloaded")
        page.wait_for_function("window.PeopleNames !== undefined")

        data = page.evaluate("""
        () => {
            return {
                people_names: PeopleNames,
                people_ids: PeopleIDs,
                available_at_slot: AvailableAtSlot,
                time_of_slot: TimeOfSlot
            };
        }
        """)

        browser.close()

    people_names = data["people_names"]
    people_ids = data["people_ids"]
    available_at_slot = data["available_at_slot"]
    time_of_slot = data["time_of_slot"]

    header = ["time"] + people_names
    rows = []

    for unix_time, slot in zip(time_of_slot, available_at_slot):
        dt = datetime.fromtimestamp(unix_time)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        available = set(slot)
        row = [time_str]

        for pid in people_ids:
            row.append("o" if pid in available else "")

        rows.append(row)

    write_csv(args.output, header, rows)
    print(f"CSV saved to {args.output}")

if __name__ == "__main__":
    main()
