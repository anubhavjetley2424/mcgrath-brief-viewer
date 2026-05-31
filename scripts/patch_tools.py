"""Patch tools.py to add the search_domain_listing_for_address function."""
import os

TOOLS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..",
    "MAS Sydney Residental Home Developement Approvals",
    "tools.py",
)
TOOLS_PATH = os.path.normpath(TOOLS_PATH)

NEW_FUNC = r'''

@mcp.tool()
async def search_domain_listing_for_address(address: str, suburb: str, postcode: str) -> str:
    """Search Domain.com.au for a specific property address to retrieve listing
    details (lot size, bedrooms, bathrooms, price) and listing images.

    Works for properties currently listed OR recently sold.
    Tries sold listings first (more reliable data), then active listings.
    Returns JSON with listing details + image URLs.
    """
    suburb_slug = suburb.strip().lower().replace(" ", "-")
    street_key = address.split(",")[0].strip().lower()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MAS-Sydney/1.0)"}

    result: dict = {
        "address": address,
        "listing_url": None,
        "listing_price": None,
        "lot_size": None,
        "bedrooms": None,
        "bathrooms": None,
        "parking_spaces": None,
        "dwelling_type": None,
        "images": [],
        "source": None,
    }

    urls_to_try = [
        (f"https://www.domain.com.au/sold-listings/{suburb_slug}-nsw-{postcode}/?sort=solddate-desc", "domain_sold"),
        (f"https://www.domain.com.au/sale/{suburb_slug}-nsw-{postcode}/?excludeunderoffer=1", "domain_active"),
    ]

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for search_url, source_label in urls_to_try:
            try:
                r = await client.get(search_url, timeout=15.0)
                if r.status_code != 200:
                    continue
                html = r.text

                street_tokens = [t for t in street_key.split() if len(t) > 2]
                listing_links = re.findall(
                    r'href="(https://www\.domain\.com\.au/[^"]+)"',
                    html, re.IGNORECASE,
                )
                matched_link = None
                for link in listing_links:
                    link_lower = link.lower()
                    if suburb_slug in link_lower and all(t in link_lower for t in street_tokens):
                        matched_link = link
                        break

                if matched_link:
                    result["listing_url"] = matched_link
                    result["source"] = source_label

                    try:
                        listing_r = await client.get(matched_link, timeout=15.0)
                        if listing_r.status_code == 200:
                            listing_html = listing_r.text

                            lot_m = re.search(r'(\d{2,5})\s*m[' + '\u00b2' + r'2]', listing_html)
                            if lot_m:
                                result["lot_size"] = int(lot_m.group(1))

                            bed_m = re.search(r'(\d+)\s*(?:bed|Bed)', listing_html)
                            if bed_m:
                                result["bedrooms"] = int(bed_m.group(1))

                            bath_m = re.search(r'(\d+)\s*(?:bath|Bath)', listing_html)
                            if bath_m:
                                result["bathrooms"] = int(bath_m.group(1))

                            park_m = re.search(r'(\d+)\s*(?:car|Car|parking|garage)', listing_html)
                            if park_m:
                                result["parking_spaces"] = int(park_m.group(1))

                            price_m = re.search(r'\$\s?([\d,]{6,12})', listing_html)
                            if price_m:
                                try:
                                    result["listing_price"] = int(price_m.group(1).replace(",", ""))
                                except ValueError:
                                    pass

                            html_lower = listing_html.lower()
                            if "townhouse" in html_lower:
                                result["dwelling_type"] = "Townhouse"
                            elif "duplex" in html_lower:
                                result["dwelling_type"] = "Duplex"
                            elif "apartment" in html_lower or "unit" in html_lower:
                                result["dwelling_type"] = "Apartment"
                            elif "house" in html_lower:
                                result["dwelling_type"] = "House"

                            img_patterns = [
                                r'https?://[^"\s]+?bucket-api\.domain\.com\.au/v1/bucket/image/[^"\s]+?(?:/2000x1500|/1500x1000|/1144x888|/660x495)[^"\s]*',
                                r'https?://[^"\s]+?rimh2\.domainstatic\.com\.au/[^"\s]+?(?:\.jpg|\.jpeg|\.png|\.webp)',
                            ]
                            img_seen = set()
                            for pat in img_patterns:
                                for im in re.finditer(pat, listing_html, re.IGNORECASE):
                                    u = im.group(0).split('"')[0].split("'")[0]
                                    if u not in img_seen:
                                        result["images"].append({"url": u, "kind": "photo"})
                                        img_seen.add(u)
                                    if len(result["images"]) >= 12:
                                        break

                            og = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', listing_html, re.IGNORECASE)
                            if og and og.group(1) not in img_seen:
                                result["images"].insert(0, {"url": og.group(1), "kind": "photo"})
                    except Exception:
                        pass

                    break
            except Exception:
                continue

    return json.dumps(result)

'''

# Read the file
with open(TOOLS_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Find the insertion point: after scrape_listing_images_simple's return statement,
# before the @mcp.tool() decorator of get_satellite_and_terrain_data
marker = 'return json.dumps({"images": images, "count": len(images)})'
# Find the SECOND occurrence (first is in a different function)
idx = content.find(marker)
if idx == -1:
    print(f"ERROR: Could not find marker in {TOOLS_PATH}")
    exit(1)

# Find the next @mcp.tool() after this marker
next_mcp = content.find("@mcp.tool()", idx + len(marker))
if next_mcp == -1:
    print("ERROR: Could not find next @mcp.tool() after marker")
    exit(1)

# Verify it's the get_satellite_and_terrain_data function
check = content[next_mcp:next_mcp+200]
if "get_satellite_and_terrain_data" not in check:
    print(f"WARNING: Next @mcp.tool() is not get_satellite_and_terrain_data: {check[:80]}")

# Insert the new function between the return statement and the @mcp.tool() decorator
insert_point = idx + len(marker)
# Find the end of this line (accounting for \r\n or \n)
while insert_point < len(content) and content[insert_point] in ('\r', '\n'):
    insert_point += 1

# Now insert before the blank lines before @mcp.tool()
# Go back to the start of the blank lines
new_content = content[:insert_point] + NEW_FUNC + "\n" + content[next_mcp:]

with open(TOOLS_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"SUCCESS: Patched {TOOLS_PATH}")
print(f"  - Added search_domain_listing_for_address function")
print(f"  - Inserted at character offset {insert_point}")
