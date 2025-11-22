#!/usr/bin/env python3

import argparse
import csv
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    
    print("Starting archive script...", flush=True)
    
    csv_path = Path(__file__).parent / "all_keys.csv"
    stats_path = Path(__file__).parent / "archive_stats.txt"
    
    archived = 0
    skipped = 0
    
    with open(stats_path, 'w') as f:
        f.write(f"new_archives=0\n")
        f.write(f"already_archived=0\n")
        f.write(f"failed=0\n")
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found", flush=True)
        return 1
    
    print(f"Loading CSV from {csv_path}...", flush=True)
    records = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    
    print(f"Loaded {len(records)} records", flush=True)
    start_time = time.time()
    
    for i, row in enumerate(records):
        if time.time() - start_time > args.timeout:
            print(f"\nTimeout reached after {i} records", flush=True)
            break
        
        if row.get('wayback_url'):
            skipped += 1
            continue
        
        if row.get('removed'):
            continue
        
        url = f"http://download.tplinkcloud.com/{row['fullpath']}"
        print(f"[{i+1}/{len(records)}] Archiving: {row['fullpath']}", flush=True)
        
        try:
            save_url = f"https://web.archive.org/save/{url}"
            req = urllib.request.Request(save_url, headers={'User-Agent': 'TP-Link Archive Bot'})
            
            with urllib.request.urlopen(req, timeout=60) as response:
                content_location = response.headers.get('Content-Location')
                if content_location:
                    row['wayback_url'] = f"https://web.archive.org{content_location}"
                else:
                    row['wayback_url'] = response.geturl()
                
                print(f"  ✓ {row['wayback_url']}", flush=True)
                archived += 1
                
                with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['creation', 'size', 'fullpath', 'added', 'removed', 'wayback_url'])
                    writer.writeheader()
                    writer.writerows(records)
                
                with open(stats_path, 'w') as f:
                    f.write(f"new_archives={archived}\n")
                    f.write(f"already_archived={skipped}\n")
                    f.write(f"failed=0\n")
        
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  Rate limited, waiting 60s...", flush=True)
                time.sleep(60)
                continue
            print(f"  ✗ HTTP {e.code}", flush=True)
        
        except Exception as e:
            print(f"  ✗ {e}", flush=True)
        
        time.sleep(2)
    
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['creation', 'size', 'fullpath', 'added', 'removed', 'wayback_url'])
        writer.writeheader()
        writer.writerows(records)
    
    with open(stats_path, 'w') as f:
        f.write(f"new_archives={archived}\n")
        f.write(f"already_archived={skipped}\n")
        f.write(f"failed=0\n")
    
    print(f"\nDone: {archived} archived, {skipped} skipped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
