import asyncio
import httpx

async def test_hazards():
    lat, lng = -33.7069, 151.0133
    extent = f"{lng-0.001},{lat-0.001},{lng+0.001},{lat+0.001}"
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": "4326",
        "mapExtent": extent,
        "imageDisplay": "800,600,96",
        "tolerance": "2",
        "returnGeometry": "false",
        "f": "json",
    }
    async with httpx.AsyncClient() as client:
        # Hazard
        try:
            r = await client.get(
                "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_Hazard/MapServer/identify",
                params=params, timeout=15.0,
            )
            data = r.json()
            results = data.get("results", [])
            print(f"Hazard layers found: {len(results)}")
            for res in results:
                name = res.get("layerName", "?")
                attrs = res.get("attributes", {})
                print(f"  - {name}")
                for k, v in list(attrs.items())[:5]:
                    print(f"    {k}: {v}")
        except Exception as e:
            print(f"Hazard FAILED: {e}")

        # EPI
        try:
            r = await client.get(
                "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_EPIs/MapServer/identify",
                params=params, timeout=15.0,
            )
            data = r.json()
            results = data.get("results", [])
            print(f"\nEPI layers found: {len(results)}")
            for res in results:
                name = res.get("layerName", "?")
                print(f"  - {name}")
        except Exception as e:
            print(f"EPI FAILED: {e}")

asyncio.run(test_hazards())
