#!/usr/bin/env python3

"""
Author: @billz <billzimmerman@gmail.com>
Author URI: https://github.com/billz

Usage: python provision.py <inventory>
    [--retries N]
    [--dry-run]
    [--concurrency N]
    [--api-url URL]
    [--apt-key KEY]

Example: python provision.py hosts.csv --dry-run

Provisions servers from an inventory file like so:
    host1,192.168.0.5
    host2,172.10.2.1

    Rudimentary IP validation is performed, along with
    concurrent processing with ThreadPoolExecutor. 
    Blank lines and comments are skipped and a dry-run
    mode is included.
    
    Todo: mock API call

Notes:
Rather than rely on an inventory file, a list of target hosts
could be obtained from the API during execution.
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
    # Todo: consider adding timeout arg
    parser = argparse.ArgumentParser(description="Provision hosts from inventory file (hostname, ipv4 per line).")
    parser.add_argument("inventory", type=Path, help="Path to inventory file (hostname, ipv4 per line).")
    parser.add_argument("--retries", type=int, default=3, help="Retries per host on transient failure")
    parser.add_argument("--dry-run", action="store_true", help="Don't call the API; just show what would be done")
    parser.add_argument("--concurrency", type=int, default=12, help="Number of concurrent workers")
    parser.add_argument("--api-url", required=False, default="https://api.example.local/", help="API URL (placeholder)")
    parser.add_argument("--api-key", required=False, default="", help="API key/auth token")
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

    max_workers = max(1, min(args.concurrency, len(valid_entries), 256))

    logging.info("Begin provisioning with %d workers (dry-run=%s)", max_workers, args.dry_run)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
        ex.submit(
            do_action,
            hostname,
            ip,
            api_url=args.api_url,
            api_key=args.api_key,
            dry_run=args.dry_run,
            retries=args.retries,
            #timeout=args.timeout,
        ): (hostname, ip)
        for hostname, ip in valid_entries
    }

def do_action(
    hostname: str,
    api_url: str,
    apt_key: str,
    dry_run: bool,
    max_retries: int,
) -> Dict:
    """
    Worker function to perform an action on a single host.
    Retry is implemented, timeout could also be added.
    Returns a dict with result
    """
    payload = {"hostname": hostname, "ip": ip}

    if dry_run:
        logging.info("DRY-RUN: calling API for %s (%s) -> payload: %s", hostname, ip, payload)
        return {"hostname": hostname, "ip": ip, "status": "dry-run", "attempts": 0}

    attempt = 0
    while attempt <= max_retries:
        attempt += 1
        try:
            # Todo: implememnt mock API call
            response = api_call(payload)

        except Exception as exc:
            logging.exception("Exception occurred while calling API for %s (%s) attempt %d: %s", hostname, ip, attempt, exc)

    return {"hostname": hostname, "ip": ip, "status": "completed", "attempts": max_retries}

def api_call(payload: Dict) -> Dict:
    """
    Simulates and API call. Returns a dict representing the result.
    """
    latency=random.uniform(0.05, 0.6) # seconds
    # Todo: call API using api_url, api_key, payload args
    # Implement return values based on status codes (200, 503, 400, etc.)

    # success example
    return {"ok": True, "status_code": 200, "body": {"message": "provisioned", "payload": payload}}

if __name__ == "__main__":
    main()

