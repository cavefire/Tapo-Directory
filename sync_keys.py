#!/usr/bin/env python3

import argparse
import csv
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class FileRecord:
    
    def __init__(self, creation: str, size: str, fullpath: str, added: Optional[str] = None, removed: Optional[str] = None, wayback_url: Optional[str] = None):
        self.creation = creation
        self.size = size
        self.fullpath = fullpath
        self.added = added or datetime.now().strftime("%Y-%m-%d")
        self.removed = removed or ""
        self.wayback_url = wayback_url or ""
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "creation": self.creation,
            "size": self.size,
            "fullpath": self.fullpath,
            "added": self.added,
            "removed": self.removed,
            "wayback_url": self.wayback_url
        }


def fetch_s3_listing(input_file: Optional[Path] = None) -> List[str]:
    if input_file and input_file.exists():
        print(f"Reading S3 listing from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(lines)} entries from file")
        return lines
    
    print("Fetching S3 listing from download.tplinkcloud.com...")
    
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "amazon/aws-cli", "s3", "ls", 
             "--recursive", "download.tplinkcloud.com/", "--no-sign-request"],
            capture_output=True,
            text=True,
            check=True
        )
        
        lines = result.stdout.strip().split("\n")
        print(f"Fetched {len(lines)} entries from S3")
        return lines
    
    except subprocess.CalledProcessError as e:
        print(f"Error fetching S3 listing: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Docker not found. Please install Docker to run this script.")
        sys.exit(1)


def parse_s3_line(line: str) -> Tuple[str, str, str] | None:
    parts = line.split(None, 3)
    
    if len(parts) != 4:
        return None
    
    date = parts[0]
    time = parts[1]
    size = parts[2]
    fullpath = parts[3]
    
    if fullpath.endswith("/"):
        return None
    
    creation = f"{date} {time}"
    return creation, size, fullpath


def extract_type_and_product(fullpath: str) -> Tuple[str, str, str] | None:
    parts = fullpath.split("/")
    
    if len(parts) < 2:
        return None
    
    file_type = parts[0]
    
    if len(parts) >= 3:
        subfolder = parts[1]
        filename = parts[-1]
    else:
        subfolder = ""
        filename = parts[1]
    
    
    match = re.match(r'^([A-Za-z][A-Za-z0-9\-]*?)\s+(?:[0-9]|en_|v[0-9]|Build|Rel|dist)', filename, re.IGNORECASE)
    
    if match:
        product = match.group(1)
        product = product.rstrip('-')
        return file_type, subfolder, product
    
    match = re.match(r'^([A-Za-z][A-Za-z0-9\-]*?)[_\(]', filename)
    
    if match:
        product = match.group(1)
        product = product.rstrip('-')
        return file_type, subfolder, product
    
    return None


def load_existing_csv(csv_path: Path) -> Dict[str, FileRecord]:
    records = {}
    
    if not csv_path.exists():
        return records
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fullpath = row['fullpath']
            records[fullpath] = FileRecord(
                creation=row['creation'],
                size=row['size'],
                fullpath=fullpath,
                added=row.get('added', ''),
                removed=row.get('removed', ''),
                wayback_url=row.get('wayback_url', '')
            )
    
    return records


def save_csv(csv_path: Path, records: List[FileRecord]):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = ['creation', 'size', 'fullpath', 'added', 'removed', 'wayback_url']
    
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        sorted_records = sorted(records, key=lambda r: r.fullpath)
        for record in sorted_records:
            writer.writerow(record.to_dict())


def sync_files(output_dir: Optional[Path] = None, input_file: Optional[Path] = None, initial_crawl: bool = False):
    if output_dir is None:
        output_dir = Path(__file__).parent
    
    s3_lines = fetch_s3_listing(input_file)
    current_files: Set[str] = set()
    file_data: Dict[str, Tuple[str, str]] = {}
    
    print("Parsing S3 listing...")
    for line in s3_lines:
        parsed = parse_s3_line(line)
        if not parsed:
            continue
        
        creation, size, fullpath = parsed
        file_data[fullpath] = (creation, size)
        current_files.add(fullpath)
    
    print(f"Found {len(current_files)} files in S3")
    
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = output_dir / "all_keys.csv"
    
    print(f"Processing {csv_path}...")
    existing_records = load_existing_csv(csv_path)
    
    is_initial_crawl = initial_crawl or len(existing_records) == 0
    added_date = "initial crawl" if is_initial_crawl else today
    
    updated_records = []
    new_urls = 0
    removed_urls = 0
    
    for fullpath in current_files:
        creation, size = file_data[fullpath]
        
        if fullpath in existing_records:
            record = existing_records[fullpath]
            record.creation = creation
            record.size = size
        else:
            record = FileRecord(creation, size, fullpath, added=added_date)
            new_urls += 1
        
        updated_records.append(record)
    
    if not is_initial_crawl:
        for fullpath, record in existing_records.items():
            if fullpath not in current_files:
                if not record.removed:
                    record.removed = today
                    removed_urls += 1
                updated_records.append(record)
    
    save_csv(csv_path, updated_records)
    print(f"  Saved {len(updated_records)} records ({len(current_files)} current, "
          f"{len(updated_records) - len(current_files)} removed)")
    
    stats_file = output_dir / "sync_stats.txt"
    with open(stats_file, 'w') as f:
        f.write(f"new_urls={new_urls}\n")
        f.write(f"removed_urls={removed_urls}\n")
    
    print(f"\nSync completed! CSV file saved: {csv_path}")
    print(f"Statistics: {new_urls} new, {removed_urls} removed")


def main():
    parser = argparse.ArgumentParser(
        description="Sync TP-Link Cloud S3 files to organized CSV files"
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for CSV files (default: script directory)'
    )
    parser.add_argument(
        '--input',
        type=Path,
        help='Input file with S3 listing (if not provided, will fetch from S3)'
    )
    parser.add_argument(
        '--initial-crawl',
        action='store_true',
        help='Treat this run as initial crawl: never mark removed, added="initial crawl"',
    )
    
    args = parser.parse_args()
    
    try:
        sync_files(args.output_dir, args.input, args.initial_crawl)
    except KeyboardInterrupt:
        print("\nSync interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during sync: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
