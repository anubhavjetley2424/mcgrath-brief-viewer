import asyncio
from playwright.async_api import async_playwright

urls = [
    'https://airtable.com/appvTX5GSGGSRHV1c/shrhVw3cM24Kk1Mke',
    'https://airtable.com/appvTX5GSGGSRHV1c/shrmccNo8lY673vSZ',
    'https://airtable.com/appvTX5GSGGSRHV1c/shrrOGHTRsgaWNLEt',
    'https://airtable.com/appvTX5GSGGSRHV1c/shrj0SClkj45Ix7LQ',
    'https://airtable.com/appvTX5GSGGSRHV1c/shrOkU7NbCJwAfVFw',
    'https://airtable.com/appvTX5GSGGSRHV1c/shr4pzOlv53l6Eyr6',
    'https://airtable.com/appvTX5GSGGSRHV1c/shrYeZHRfqn0SXvIw',
    'https://airtable.com/appvTX5GSGGSRHV1c/shr7ZdWeoljzEF4Cd'
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for url in urls:
            try:
                await page.goto(url, wait_until='networkidle')
                await page.wait_for_selector('label', timeout=10000)
                labels = await page.evaluate("() => { return Array.from(document.querySelectorAll('label')).map(el => el.innerText.trim()); }")
                h1 = await page.evaluate("() => { const el = document.querySelector('h1'); return el ? el.innerText : ''; }")
                print(f"FORM: {h1}")
                print(f"URL: {url}")
                print(f"FIELDS: {labels}\n")
            except Exception as e:
                print(f"ERROR on {url}: {e}")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
