#!/usr/bin/env python3.11
"""
lix_session.py - Linux Browser Session Cookie Extractor
Extracts session cookies from Brave and Firefox on Linux.
Exports to Cookie Editor JSON format for direct import.

Requirements:
    pip install rookiepy

Usage:
    python3.11 lix_session.py                    # Extract from Brave + Firefox
    python3.11 lix_session.py --browser brave    # Brave only
    python3.11 lix_session.py --browser firefox  # Firefox only
    python3.11 lix_session.py --domain github.com
    python3.11 lix_session.py --output cookies.json
    python3.11 lix_session.py --format header    # HTTP header format

Disclaimer: Use only on your own machine for authorized purposes.
"""

import argparse
import json
import sys
import os

try:
    import rookiepy
except ImportError:
    print("[!] rookiepy not installed. Run:")
    print("    pip3 install rookiepy")
    sys.exit(1)


BROWSERS = {
    "brave": rookiepy.brave,
    "firefox": rookiepy.firefox,
    "chrome": rookiepy.chrome,
    "chromium": rookiepy.chromium,
    "edge": rookiepy.edge,
}


def extract_cookies(browser_name, domains=None):
    """Extract cookies from specified browser."""
    if browser_name not in BROWSERS:
        print(f"[!] Unsupported browser: {browser_name}")
        print(f"    Supported: {', '.join(BROWSERS.keys())}, all")
        return []

    func = BROWSERS[browser_name]

    try:
        if domains:
            cookies = func(domains)
        else:
            cookies = func()
        return cookies
    except Exception as e:
        print(f"[!] Error extracting from {browser_name}: {e}")
        return []


def to_cookie_editor_json(cookies):
    """Convert rookiepy cookies to Cookie Editor JSON format."""
    export = []
    for c in cookies:
        entry = {
            "domain": c["domain"],
            "name": c["name"],
            "value": c["value"],
            "path": c["path"],
            "secure": c["secure"],
            "httpOnly": c["http_only"],
            "session": c["expires"] is None,
        }

        if c["expires"] is not None:
            entry["expirationDate"] = int(c["expires"])

        same_site = c.get("same_site", "")
        if isinstance(same_site, int):
            same_site_map = {0: "no_restriction", 1: "lax", 2: "strict"}
            same_site = same_site_map.get(same_site, "no_restriction")
        same_site_str = str(same_site).lower()
        if same_site_str in ("lax", "strict"):
            entry["sameSite"] = same_site_str
        elif same_site_str in ("none", "no_restriction"):
            entry["sameSite"] = "no_restriction"
        else:
            entry["sameSite"] = None

        entry["hostOnly"] = not c["domain"].startswith(".")
        entry["storeId"] = None

        export.append(entry)

    return json.dumps(export, indent=4)


def to_header_string(cookies):
    """Convert cookies to HTTP header string format."""
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def to_netscape(cookies):
    """Convert cookies to Netscape format."""
    lines = ["# Netscape HTTP Cookie File", ""]
    for c in cookies:
        domain = c["domain"]
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c["path"]
        secure = "TRUE" if c["secure"] else "FALSE"
        expires = str(int(c["expires"])) if c["expires"] else "0"
        name = c["name"]
        value = c["value"]
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
    return "\n".join(lines)


def print_summary(cookies, browser_name):
    """Print summary of extracted cookies."""
    print(f"\n{'='*60}")
    print(f"  Browser:  {browser_name}")
    print(f"  Cookies:  {len(cookies)}")
    print(f"{'='*60}")

    if not cookies:
        print("  No cookies found.")
        return

    domains = {}
    for c in cookies:
        d = c["domain"]
        domains[d] = domains.get(d, 0) + 1

    print(f"\n  Domains with cookies:")
    for domain, count in sorted(domains.items(), key=lambda x: -x[1])[:15]:
        print(f"    {domain:<40} {count:>3}")

    print(f"\n  Sample cookies (first 5):")
    for c in cookies[:5]:
        val = c["value"][:40] + "..." if len(c["value"]) > 40 else c["value"]
        print(f"    {c['domain']:<30} {c['name']:<25} = {val}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="lix_session.py - Linux Browser Cookie Extractor (Brave/Firefox)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                # Extract Brave + Firefox (default)
  %(prog)s --browser brave                # Brave only
  %(prog)s --browser firefox              # Firefox only
  %(prog)s --browser all                  # All browsers
  %(prog)s --domain github.com            # Filter by domain
  %(prog)s --domain github.com --domain google.com
  %(prog)s --output cookies.json          # Save to file
  %(prog)s --format header                # HTTP header format
  %(prog)s --format netscape --output cookies.txt
        """,
    )
    parser.add_argument(
        "-b", "--browser",
        default="all",
        help="Browser: brave, firefox, chrome, chromium, edge, all (default: all)",
    )
    parser.add_argument(
        "-d", "--domain",
        action="append",
        help="Filter by domain (can be specified multiple times)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "header", "netscape"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary output",
    )

    args = parser.parse_args()

    browser_input = args.browser.lower()

    if browser_input == "all":
        # Default: prioritize Brave and Firefox
        browser_list = ["brave", "firefox"]
    else:
        browser_list = [browser_input]

    all_cookies = []
    for browser_name in browser_list:
        if browser_name not in BROWSERS:
            print(f"[!] Unknown browser: {browser_name}")
            print(f"    Available: {', '.join(BROWSERS.keys())}, all")
            sys.exit(1)

        print(f"[*] Extracting cookies from {browser_name}...")
        cookies = extract_cookies(browser_name, args.domain)
        all_cookies.extend(cookies)

        if not args.quiet:
            print_summary(cookies, browser_name)

    if not all_cookies:
        print("[*] No cookies found.")
        print("[*] Make sure the browser is closed and cookies exist.")
        sys.exit(0)

    if args.format == "json":
        output = to_cookie_editor_json(all_cookies)
    elif args.format == "header":
        output = to_header_string(all_cookies)
    elif args.format == "netscape":
        output = to_netscape(all_cookies)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"[+] Saved {len(all_cookies)} cookies to {args.output}")
        print(f"[+] Import {args.output} into Cookie Editor extension")
    else:
        print(output)


if __name__ == "__main__":
    main()
