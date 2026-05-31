import asyncio
import httpx
import json

async def test():
    lat, lng = -33.7069, 151.0133
    url = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_Principal_Planning/MapServer/identify"
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": "4326",
        "mapExtent": f"{lng-0.003},{lat-0.003},{lng+0.003},{lat+0.003}",
        "imageDisplay": "800,600,96",
        "tolerance": "4",
        "layers": "all",
        "returnGeometry": "false",
        "f": "json",
    }
    async with httpx.AsyncClient() as c:
        r = await c.get(url, params=params, timeout=20.0)
        data = r.json()
        for result in data.get("results", []):
            name = result.get("layerName", "?")
            attrs = result.get("attributes", {})
            print(f"\nLayer: {name}")
            for k, v in list(attrs.items())[:10]:
                print(f"  {k}: {v}")

asyncio.run(test())
