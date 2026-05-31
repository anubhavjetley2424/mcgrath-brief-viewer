"""
One-off probe to verify we can scrape SSC eTrack DA search via plain HTTP.

Strategy:
  1. GET the search page → extract __VIEWSTATE, __EVENTVALIDATION, __VIEWSTATEGENERATOR
  2. POST back with those + a date-range search for the last 30 days
  3. Inspect what comes back (length, table presence, sample row format)

If this works, we don't need Playwright/Browserbase.
"""

import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from http.cookiejar import CookieJar

BASE = "https://propertydevelopment.ssc.nsw.gov.au/T1PRProd/WebApps/eProperty/P1/eTrack/eTrackApplicationSearch.aspx"
QS = "?Group=DA&ResultsFunction=SSC.P1.ETR.RESULT.DA&r=SSC.P1.WEBGUEST&f=SSC.P1.ETR.SEARCH.DA"
URL = BASE + QS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppraisalBriefBot/0.1",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
}

def fetch(opener, url, data=None, extra_headers=None):
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    if data is not None:
        data = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.url

def extract_state(html):
    state = {}
    for name in ("__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR", "__EVENTTARGET", "__EVENTARGUMENT"):
        m = re.search(rf'name="{name}"[^>]*value="([^"]*)"', html)
        state[name] = m.group(1) if m else ""
    return state

def main():
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    print("Step 1: GET search page")
    html, get_final_url = fetch(opener, URL)
    print(f"  size={len(html):,} bytes  cookies={len(list(cj))}")
    print(f"  final_url={get_final_url}")
    # Inspect the actual <form> action and the search button markup
    m_action = re.search(r'<form[^>]*action="([^"]*)"', html)
    print(f"  form_action={m_action.group(1) if m_action else 'NOT FOUND'}")
    m_btn = re.search(r'<input[^>]*name="ctl00\$Content\$btnSearch"[^>]*>', html)
    print(f"  btn_html={m_btn.group(0) if m_btn else 'NOT FOUND'}")
    state = extract_state(html)
    for k, v in state.items():
        print(f"  {k} length={len(v)}")

    date_to = date.today()
    date_from = date_to - timedelta(days=30)
    df = date_from.strftime("%d/%m/%Y")
    dt = date_to.strftime("%d/%m/%Y")
    print(f"\nStep 2: POST search  Date From={df}  Date To={dt}")

    payload = {
        "__VIEWSTATE": state["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR": state["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION": state["__EVENTVALIDATION"],
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "ctl00$Content$txtApplicationID$txtText": "",
        "ctl00$Content$txtDateFrom$txtText": df,
        "ctl00$Content$txtDateTo$txtText": dt,
        "ctl00$Content$txtSuburb$txtText": "",
        "ctl00$Content$txtDescription$txtText": "",
        "ctl00$Content$txtStreetNoFrom$txtText": "",
        "ctl00$Content$txtStreetNoTo$txtText": "",
        "ctl00$Content$txtStreet$txtText": "",
        "ctl00$Content$txtStreetType$txtText": "",
        "ctl00$Content$ddlApplicationType$elbList": "",
        "ctl00$Content$btnSearch": "Search",
    }
    # POST to the GET's final URL (with session token), not the original
    result_html, final_url = fetch(opener, get_final_url, data=payload)
    print(f"  size={len(result_html):,} bytes  final_url={final_url}")

    # Hints about results
    has_table = "<table" in result_html.lower()
    da_links = re.findall(r'href="[^"]*ApplicationDetails[^"]*"', result_html, re.IGNORECASE)
    da_ids = re.findall(r'\bDA\d{2}[/\-]\d{3,5}\b', result_html)
    no_results = "no results" in result_html.lower() or "no records" in result_html.lower()

    print(f"\nDiagnostics:")
    print(f"  has_table: {has_table}")
    print(f"  detail_links_found: {len(da_links)}")
    print(f"  da_ids_found: {len(da_ids)}  sample: {da_ids[:5]}")
    print(f"  no_results_message: {no_results}")

    # Save the response HTML for inspection
    out = "scripts/ssc_search_result.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(result_html)
    print(f"\nSaved response to: {out}")

if __name__ == "__main__":
    main()
