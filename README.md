# Admin-Panel-Finder

Admin-Panel-Finder is a small, fast Python tool to help locate administrative panels and common endpoints on web sites by probing a list of paths. It performs optional multithreaded scans, checks robots.txt, reports HTTP responses (200, 301/302 redirects, 404, etc.), and provides simple filtering by file type.

---

## Features

- Scan a target host for common admin panels and endpoints using a wordlist.
- Optional multithreaded scanning for faster results.
- Detects 200 (found), 3xx (redirects — flagged as potential EAR/redirect), 404 (not found), timeouts and errors.
- Robots.txt fetch and display.
- Filter candidate paths by type (php, asp, html, all).
- Configurable timeouts and thread count.
- Simple, portable: Python 3 + requests.

---

## Requirements

- Python 3.6+ (Python 3.8+ recommended)
- pip
- Python package: requests

Install requests:

```bash
pip install requests
```

---

## Installation

```bash
pkg install git
git clone https://github.com/Safin-Mohammad/Admin-Panel-Finder
cd Admin-Panel-Finder
```

---

## Usage

Basic usage:

```bash
python3 admin-finder.py -u example.com
```

Options:

- `-u`, `--target` (required) — Target host or URL. Examples: `example.com`, `https://example.com`
- `--prefix` — Custom path prefix appended to the base (e.g. `/site`). Default: `""`
- `--type` — Filter paths by type. One of: `php`, `asp`, `html`, `all` (default: `all`)
- `--fast` — Enable multithreaded scanning
- `--threads` — Number of threads when `--fast` is used (default: 10)
- `--wordlist` — Wordlist file to use (default: `paths.txt`)
- `--timeout` — Request timeout in seconds (default: 6.0)

Examples:

- Sequential scan using default wordlist:
  ```bash
  python3 admin-finder.py -u example.com
  ```

- Fast (multithreaded) scan using 20 threads:
  ```bash
  python3 admin-finder.py -u example.com --fast --threads 20
  ```

- Scan with a prefix and php-only filter:
  ```bash
  python3 admin-finder.py -u https://example.com --prefix /blog --type php
  ```

- Use a custom wordlist and longer timeout:
  ```bash
  python3 admin-finder.py -u example.com --wordlist my_paths.txt --timeout 10
  ```

---

## Behavior Details

- The tool normalizes the target: if no scheme is supplied the tool defaults to `http://`.
- If `--prefix` is specified it is appended to the normalized base URL (ensuring appropriate slashes).
- Robots.txt is fetched and printed (helps you find interesting entries).
- Requests are made with a timeout and a simple User-Agent header.
- Redirects are not followed when checking each path (so 302/301 responses are reported).
- Output is written to stdout (console). You can redirect output to a file if you want to save results:
  ```bash
  python3 admin-finder.py -u example.com > scan_results.txt
  ```

---

## Examples of output

- 200 responses: reported as resource found
- 301/302 responses: reported as potential EAR/vulnerability or redirect
- 404 responses: reported as not found
- timeouts / network errors: reported with an error message

A summary with counts for each response category is printed at the end.

---

## Safety, Legality, and Responsible Use

- Only use Admin-Panel-Finder on systems you own or are expressly authorized to test.
- Scanning others' systems without permission is illegal in many jurisdictions and may lead to criminal or civil liability.
- This tool performs automated HTTP requests — treat the usage carefully to avoid impacting targets (use fewer threads, increase timeouts).
- If you discover a vulnerability, follow responsible disclosure guidelines: notify the site owner or use the project's official disclosure process (if applicable).

---

## Troubleshooting

- If you see many timeouts: try increasing `--timeout` or reducing `--threads`.
- If the tool returns HTML for robots.txt or fails to fetch it, check that the base URL is correct (http vs https) and that the host is reachable.
- If the wordlist seems to be ignored, confirm file encoding and that it's not empty and not filtered by `--type`.

---

