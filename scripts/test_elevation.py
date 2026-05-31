import asyncio
import httpx

async def test_elevation():
    lat, lng = -33.7069, 151.0133
    offset_lat = lat + 0.00027

    async with httpx.AsyncClient() as client:
        # Test Open-Meteo (most reliable free endpoint)
        try:
            url = "https://api.open-meteo.com/v1/elevation"
            params = {"latitude": f"{lat},{offset_lat}", "longitude": f"{lng},{lng}"}
            r = await client.get(url, params=params, timeout=10.0)
            data = r.json()
            elevations = data.get("elevation", [])
            print(f"Open-Meteo: {elevations}")
            if len(elevations) >= 2:
                diff = abs(elevations[0] - elevations[1])
                slope = (diff / 30.0) * 100
                print(f"  Elevation diff: {diff:.2f}m, Slope: {slope:.1f}%")
        except Exception as e:
            print(f"Open-Meteo FAILED: {e}")

        # Test Open-Elevation
        try:
            url = "https://api.open-elevation.com/api/v1/lookup"
            params = {"locations": f"{lat},{lng}|{offset_lat},{lng}"}
            r = await client.get(url, params=params, timeout=15.0)
            data = r.json()
            results = data.get("results", [])
            print(f"\nOpen-Elevation: {[r.get('elevation') for r in results]}")
        except Exception as e:
            print(f"\nOpen-Elevation FAILED: {e}")

asyncio.run(test_elevation())
