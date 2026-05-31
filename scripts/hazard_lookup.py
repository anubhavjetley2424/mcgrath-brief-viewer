"""
Per-deal hazard lookup against NSW Planning Portal ePlanning ArcGIS service.

Given a lat/lng (subject property), returns flags + matched feature labels for:
  - Flood Planning Map
  - Bushfire Prone Land
  - Landslide Risk Land

Used at brief generation time. No persistent storage — transient per deal.

Usage:
    python hazard_lookup.py -34.062675 151.155000      # one address
    python hazard_lookup.py --self-test                # built-in test points
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

ARCGIS_BASE = (
    "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
    "ePlanning/Planning_Portal_Hazard/MapServer"
)

LAYERS = {
    "flood":     230,    # Flood Planning Map
    "bushfire":  229,    # Bushfire Prone Land
    "landslide": 232,    # Landslide Risk Land
}

HEADERS = {"User-Agent": "AppraisalBriefBot/0.1 hazard-lookup", "Accept": "application/json"}
HTTP_TIMEOUT = 30


def query_layer(layer_id: int, lat: float, lng: float, max_retries: int = 3) -> list[dict]:
    """Return the list of features at the given point. Empty list = not in zone.

    Retries on 5xx (the ArcGIS endpoint occasionally 502s)."""
    import time as _time
    params = {
        "geometry":      f"{lng},{lat}",       # ArcGIS expects X,Y == lng,lat
        "geometryType":  "esriGeometryPoint",
        "inSR":          "4326",                # WGS84 — server reprojects to layer SR
        "spatialRel":    "esriSpatialRelIntersects",
        "returnGeometry": "false",
        "outFields":     "*",
        "f":             "json",
    }
    url = f"{ARCGIS_BASE}/{layer_id}/query?{urllib.parse.urlencode(params)}"
    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                data = json.loads(resp.read())
            return data.get("features", []) or []
        except urllib.error.HTTPError as e:
            last_err = e
            if 500 <= e.code < 600:
                _time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err if last_err else RuntimeError("query_layer: exhausted retries")


def lookup(lat: float, lng: float) -> dict:
    result = {"lat": lat, "lng": lng, "hazards": {}}
    for name, layer_id in LAYERS.items():
        try:
            features = query_layer(layer_id, lat, lng)
            # Pull a representative label/description from the first matched feature
            label = None
            if features:
                attrs = features[0].get("attributes") or {}
                for key in ("d_Category", "d_Guidelin", "LAY_CLASS", "PURPOSE", "LAY_NAME", "DESCRIPTION", "Category", "CATEGORY", "name", "Label"):
                    if attrs.get(key):
                        label = attrs[key]
                        break
            result["hazards"][name] = {
                "in_zone": bool(features),
                "match_count": len(features),
                "label": label,
            }
        except Exception as e:
            result["hazards"][name] = {"in_zone": None, "error": f"{type(e).__name__}: {e}"}
    return result


def self_test():
    test_points = [
        ("Cronulla beachfront-ish (Coast Ave)", -34.062675, 151.155000),
        ("Sylvania Waters (canal estate)",      -34.020,    151.105),
        ("Bangor (inland bushland)",            -34.018,    151.025),
        ("Miranda CBD (built up)",              -34.034,    151.103),
    ]
    for label, lat, lng in test_points:
        print(f"--- {label} ({lat}, {lng}) ---")
        r = lookup(lat, lng)
        for hz, info in r["hazards"].items():
            mark = "⚠" if info.get("in_zone") else "·"
            extra = f"  [{info['label']}]" if info.get("label") else ""
            err = f"  ERR: {info['error']}" if info.get("error") else ""
            print(f"  {mark} {hz:<10} in_zone={info.get('in_zone')}{extra}{err}")
        print()


def main():
    if "--self-test" in sys.argv:
        self_test()
        return
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    lat = float(sys.argv[1])
    lng = float(sys.argv[2])
    print(json.dumps(lookup(lat, lng), indent=2))


if __name__ == "__main__":
    main()
