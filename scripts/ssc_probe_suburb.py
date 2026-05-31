"""Probe: suburb-only search vs date-range. Compare result counts."""
import re
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE = "https://propertydevelopment.ssc.nsw.gov.au/T1PRProd/WebApps/eProperty/P1/eTrack/eTrackApplicationSearch.aspx"
QS = "?Group=DA&ResultsFunction=SSC.P1.ETR.RESULT.DA&r=SSC.P1.WEBGUEST&f=SSC.P1.ETR.SEARCH.DA"
URL = BASE + QS

HEADERS = {
    "User-Agent": "Mozilla/5.0 AppraisalBriefBot/0.1",
    "Accept": "text/html",
}

def fetch(opener, url, data=None):
    h = dict(HEADERS)
    if data is not None:
        data = urllib.parse.urlencode(data).encode("utf-8")
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    with opener.open(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace"), r.url

def state(page):
    s = {}
    for n in ("__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"):
        m = re.search(rf'name="{n}"[^>]*value="([^"]*)"', page)
        s[n] = m.group(1) if m else ""
    return s

def base_payload(st):
    return {
        "__VIEWSTATE": st["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR": st["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION": st["__EVENTVALIDATION"],
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "ctl00$Content$txtApplicationID$txtText": "",
        "ctl00$Content$txtDateFrom$txtText": "",
        "ctl00$Content$txtDateTo$txtText": "",
        "ctl00$Content$txtSuburb$txtText": "",
        "ctl00$Content$txtDescription$txtText": "",
        "ctl00$Content$txtStreetNoFrom$txtText": "",
        "ctl00$Content$txtStreetNoTo$txtText": "",
        "ctl00$Content$txtStreet$txtText": "",
        "ctl00$Content$txtStreetType$txtText": "",
        "ctl00$Content$ddlApplicationType$elbList": "",
        "ctl00$Content$btnSearch": "Search",
    }

def run_search(label, modifications):
    cj = CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    page, url = fetch(op, URL)
    p = base_payload(state(page))
    p.update(modifications)
    page, url = fetch(op, url, data=p)
    rows = re.findall(r'<tr class="(?:normalRow|alternateRow)">', page)
    ids = sorted(set(re.findall(r'<a[^>]*>([A-Z]{2,4}\d{2}/\d{3,5})</a>', page)))
    has_next = bool(re.search(r'name="ctl00\$Content\$btnNext"', page))
    has_no_results = "no results" in page.lower() or "no records" in page.lower() or "exceeded" in page.lower()
    # also look for any limit-warning message
    warn_msgs = re.findall(r'<span[^>]*(?:warn|error|info|message)[^>]*>([^<]+)</span>', page, re.IGNORECASE)
    print(f"--- {label}")
    print(f"  rows={len(rows)}  ids={len(ids)}  next_btn={has_next}  no_results_msg={has_no_results}")
    print(f"  ids sample: {ids[:5]}")
    if warn_msgs:
        print(f"  page messages: {warn_msgs[:3]}")
    return ids

# Test 1: full 30-day window
a = run_search("date_range 30 days", {
    "ctl00$Content$txtDateFrom$txtText": "26/04/2026",
    "ctl00$Content$txtDateTo$txtText": "26/05/2026",
})
# Test 2: suburb only CRONULLA
b = run_search("suburb=CRONULLA only", {
    "ctl00$Content$txtSuburb$txtText": "CRONULLA",
})
# Test 3: suburb + date range (narrow)
c = run_search("suburb=CRONULLA + last 90 days", {
    "ctl00$Content$txtSuburb$txtText": "CRONULLA",
    "ctl00$Content$txtDateFrom$txtText": "26/02/2026",
    "ctl00$Content$txtDateTo$txtText": "26/05/2026",
})
# Test 4: 1 week window
d = run_search("date_range 7 days", {
    "ctl00$Content$txtDateFrom$txtText": "19/05/2026",
    "ctl00$Content$txtDateTo$txtText": "26/05/2026",
})
# Test 5: 1 year window
e = run_search("date_range 1 year", {
    "ctl00$Content$txtDateFrom$txtText": "26/05/2025",
    "ctl00$Content$txtDateTo$txtText": "26/05/2026",
})
