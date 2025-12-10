#!/usr/bin/env python3

"""
Author: @billz <billzimmerman@gmail.com>
Author URI: https://github.com/billz

Usage: python provision.py hosts.csv

Provisions servers from an inventory file like so:
    host1,192.168.0.5
    host2,172.10.2.1

    Reduimentary IP validation is performed, along with 
    concurrent processing with ThreadPoolExecutor. 
    Blank lines and comments are skipped and a dry-run
    mode is included.
    
    Todo: mock API call
"""

import argparse
import csv
import ipaddress
import logging
import random
import sys
import time

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Tuple

# logging
logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
)

def parse_inventory(path: Path) -> Tuple[list, list]:
    """
    Parse the inventory file. Returns valid entries, errors
    valid_entries: list of (hostname, ip_str)
    errors: list of (line_num, raw_line, reason)
    """
    valid = []
    errors = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, start=1):
            # skip empty rows
            if not row or (len(row) == 1 and row[0].strip() == ""):
                continue
            
            # skip comment lines
            if row[0].strip().startswith("#"):
                continue

            # more than 2 columns, join extras into second field:
            if len(row) >= 2:
                hostname = row[0].strip()
                ip_str = row[1].strip()
            else:
                # single column, maybe "host,ip" wasn't split due to double-quoting
                parts = row[0].split(",", 1)
                if len(parts) == 2:
                    hostname, ip_str = parts[0].strip(), parts[1].strip()
                else:
                    errors.append((i, row, "expected 'hostname,ip'"))
                    continue

            if hostname == "" or ip_str == "":
                #errors.append((i, row, "empty hostname or IP"))
                continue

            # validate IP
            try:
                _ = ipaddress.ip_address(ip_str)
            except ValueError:
                errors.append((i, row, f"invalid IP: {ip_str}"))
                continue

            valid.append((hostname, ip_str))

    return valid, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Provision hosts from inventory file (hostname, ipv4 per line).")
    parser.add_argument("inventory", type=Path, help="Path to inventory file (hostname, ipv4 per line).")
    parser.add_argument("--retries", type=int, default=3, help="Retries per host on transient failure")
    parser.add_argument("--dry-run", action="store_true", help="Don't call the API; just show what would be done")
    args = parser.parse_args(argv)

    if not args.inventory.exists():
        logging.error("Inventory file not found: %s", args.inventory)
        sys.exit(2)

    valid_entries, parse_errors = parse_inventory(args.inventory)
    logging.info("Parsed inventory: %d valid entries, %d parse errors", len(valid_entries), len(parse_errors))

    if parse_errors:
        for ln, raw, reason in parse_errors:
            logging.warning("Parse error line %d: %s -> %s", ln, raw, reason)

    if not valid_entries:
        logging.info("No valid entries to process. Exiting.")

    results = []

if __name__ == "__main__":
    main()

