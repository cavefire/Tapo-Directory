# TP-Link Cloud File Archive

Automated archive of all files available on TP-Link's cloud storage at `download.tplinkcloud.com`.

This repository does not host any firmware or software files. It only maintains a catalog of publicly available files and their archive links.

## Overview

This repository maintains a daily-updated catalog of all firmware, applications, and other files hosted on TP-Link's public S3 bucket. All files are archived to the Internet Archive's Wayback Machine for long-term preservation.

## What It Does

The automation runs daily and performs two tasks:

1. **Sync Script** - Fetches the complete file listing from TP-Link's S3 bucket and updates `all_keys.csv` with:
   - File creation date and size
   - Date when file was first detected
   - Date when file was removed (if applicable)
   - Wayback Machine archive URL

2. **Archive Script** - Submits unarchived files to the Internet Archive's Wayback Machine to ensure permanent preservation of TP-Link firmware and software releases. Limited to 5 minutes per day to preserve GitHub Actions quota.

## File Format

`all_keys.csv` contains the following fields:

- `creation` - File creation timestamp from S3
- `size` - File size in bytes
- `fullpath` - Full path on download.tplinkcloud.com
- `added` - Date when this file was first detected
- `removed` - Date when file was removed from S3 (empty if still available)
- `wayback_url` - Internet Archive URL (empty if not yet archived)

## Automation

The GitHub Actions workflow runs daily at 2:00 AM UTC. Each run:

- Fetches current S3 listing
- Updates the CSV with new/removed files
- Archives new files to Wayback Machine (5 minutes time limit per run)
- Commits changes with statistics on new/removed URLs and archives

## Manual Usage

To run the scripts locally:

```bash
./sync_keys.py
./archive_files.py --timeout 300
```

Docker is required for S3 access (uses the `amazon/aws-cli` container).

## Legal Notice

This repository contains only a list of publicly accessible URLs and does not host any firmware, software, or copyrighted content. All files referenced remain on TP-Link's servers and are subject to TP-Link's copyright and terms of service. This catalog is provided for archival and research purposes under fair use principles.
