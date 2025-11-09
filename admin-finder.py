#!/usr/bin/env python3
"""
Admin-Finder - improved and bugfixed version(v0.2).
Author - Safin Mohammad
Key improvements/fixes:
- Proper argparse validation and helpful options
- Correct handling of target URLs including https
- Fixed Python 3 slicing bug (len/2 float -> integer)
- Uses ThreadPoolExecutor for concurrency (safe & configurable)
- Detects 302 by using allow_redirects=False
- Adds timeouts, User-Agent, and better exception handling
- Safer path joining using urllib.parse.urljoin
- Robust wordlist parsing (skips blank lines/comments)
- Prints summary counts
"""

import argparse
import concurrent.futures
import sys
from urllib.parse import urlparse, urljoin
import requests
from requests.exceptions import RequestException, Timeout

# Colors
C_ERR = "\033[1;31m"
C_OK = "\033[1;32m"
C_INFO = "\033[1;34m"
C_RESET = "\033[0m"

BANNER = f"""{C_INFO}
  ___      _           _        ______ _           _           
 / _ \    | |         (_)       |  ___(_)         | |          
/ /_\ \ __| |_ __ ___  _ _ __   | |_   _ _ __   __| | ___ _ __ 
|  _  |/ _` | '_ ` _ \| | '_ \  |  _| | | '_ \ / _` |/ _ \ '__|
| | | | (_| | | | | | | | | | | | |   | | | | | (_| |  __/ |   
\_| |_/\__,_|_| |_| |_|_|_| |_| \_|   |_|_| |_|\__,_|\___|_|

                          {C_RESET}Made {C_ERR}!😸{C_RESET} By Safin Mohammad{C_INFO}"""

def parse_args():
    p = argparse.ArgumentParser(description="Breacher - directory/endpoint scanner (improved)")
    p.add_argument("-u", "--target", required=True, help="Target host or URL (e.g. example.com or https://example.com)")
    p.add_argument("--prefix", help="Custom path prefix to append to the host (e.g. /site)", default="")
    p.add_argument("--type", help="Filter paths by type", choices=["php", "asp", "html", "all"], default="all")
    p.add_argument("--fast", help="Use multithreading", action="store_true")
    p.add_argument("--threads", help="Number of threads to use when --fast (default 10)", type=int, default=10)
    p.add_argument("--wordlist", help="Paths wordlist file (default: paths.txt)", default="paths.txt")
    p.add_argument("--timeout", help="Request timeout in seconds (default: 6)", type=float, default=6.0)
    return p.parse_args()

def normalize_base(target, prefix):
    # If scheme missing, default to http://
    parsed = urlparse(target if "://" in target else "http://" + target)
    if not parsed.scheme:
        scheme = "http"
    else:
        scheme = parsed.scheme
    netloc = parsed.netloc or parsed.path  # if user passed 'example.com' parsed.path holds it
    base = f"{scheme}://{netloc}"
    # ensure prefix starts with '/' and does not end with '/'
    if prefix:
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        prefix = prefix.rstrip("/")
        base = base.rstrip("/") + prefix
    return base

def read_paths(wordlist, type_filter):
    try:
        with open(wordlist, "r", encoding="utf-8", errors="ignore") as f:
            raw = [line.strip() for line in f]
    except IOError:
        print(f"{C_ERR}[-]{C_RESET} Wordlist not found: {wordlist}")
        sys.exit(1)

    paths = []
    for line in raw:
        if not line or line.startswith("#"):
            continue
        path = line.lstrip("/")  # keep paths relative
        # filter similar to original: skip lines that contain other types
        if type_filter != "all":
            # original logic checked substrings; we follow a conservative approach:
            lower = path.lower()
            if type_filter == "php" and ("asp" in lower or "html" in lower):
                continue
            if type_filter == "asp" and ("php" in lower or "html" in lower):
                continue
            if type_filter == "html" and ("asp" in lower or "php" in lower):
                continue
        paths.append("/" + path)  # store with leading slash to make joining predictable
    return paths

def probe_url(session, base, path, timeout):
    url = urljoin(base + ("" if base.endswith("/") else "/"), path.lstrip("/"))
    try:
        # We set allow_redirects=False to detect 302 responses properly.
        r = session.get(url, allow_redirects=False, timeout=timeout)
        code = r.status_code
        if code == 200:
            print(f"  {C_OK}[+]{C_RESET} Admin panel (or resource) found: {url}")
            return ("found", url, code)
        elif code == 404:
            print(f"  {C_ERR}[-]{C_RESET} {url} (404)")
            return ("notfound", url, code)
        elif code in (301, 302, 303, 307, 308):
            print(f"  {C_OK}[+]{C_RESET} Potential EAR / redirect found: {url} ({code})")
            return ("redirect", url, code)
        else:
            print(f"  {C_ERR}[-]{C_RESET} {url} ({code})")
            return ("other", url, code)
    except Timeout:
        print(f"  {C_ERR}[-]{C_RESET} {url} (timeout)")
        return ("timeout", url, None)
    except RequestException as e:
        print(f"  {C_ERR}[-]{C_RESET} {url} (error: {e})")
        return ("error", url, None)

def main():
    args = parse_args()
    print(BANNER)
    print(f"\n  I am not responsible for your actions. If target doesn't respond, errors may occur.\n")
    print(f"{C_ERR}--------------------------------------------------------------------------{C_RESET}\n")

    base = normalize_base(args.target, args.prefix)
    headers = {"User-Agent": "Breacher/1.0 (+https://github.com/)"}
    session = requests.Session()
    session.headers.update(headers)

    # Check robots.txt quickly (allow redirects)
    try:
        r = session.get(urljoin(base + "/", "robots.txt"), timeout=args.timeout)
        content = r.text
        if "<html" in content.lower() and r.status_code >= 400:
            print(f"  {C_ERR}[-]{C_RESET} Robots.txt not found or returned HTML\n")
        else:
            print(f"  {C_OK}[+]{C_RESET} Robots.txt fetched. Check for interesting entries:\n")
            print(content.strip() + "\n")
    except RequestException:
        print(f"  {C_ERR}[-]{C_RESET} Robots.txt not found or could not be fetched\n")

    print(f"{C_ERR}--------------------------------------------------------------------------{C_RESET}\n")

    paths = read_paths(args.wordlist, args.type)
    if not paths:
        print(f"{C_ERR}[-]{C_RESET} No paths to scan (wordlist empty or filtered out).")
        sys.exit(1)

    results = []
    if args.fast:
        workers = max(1, args.threads)
        print(f"{C_INFO}[*]{C_RESET} Starting threaded scan with {workers} workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(probe_url, session, base, p, args.timeout) for p in paths]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as e:
                    print(f"{C_ERR}[-]{C_RESET} Worker error: {e}")
    else:
        print(f"{C_INFO}[*]{C_RESET} Starting sequential scan...")
        for p in paths:
            results.append(probe_url(session, base, p, args.timeout))

    # summary
    summary = {}
    for r in results:
        if not r:
            continue
        summary[r[0]] = summary.get(r[0], 0) + 1

    print(f"\n{C_ERR}--------------------------------------------------------------------------{C_RESET}")
    print(f"Scan summary for base: {base}")
    for k in ("found", "redirect", "notfound", "timeout", "error", "other"):
        if k in summary:
            label = k
            count = summary[k]
            print(f"  {k}: {count}")
    print(f"{C_ERR}--------------------------------------------------------------------------{C_RESET}")

if __name__ == "__main__":
    main()
