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
                # Wait for the form title to render
                await page.wait_for_selector('h1', timeout=10000)
                title = await page.title()
                h1 = await page.evaluate("() => { const el = document.querySelector('h1'); return el ? el.innerText : ''; }")
                print(f"{url}: TITLE={title} | H1={h1}")
            except Exception as e:
                print(f"{url}: ERROR {e}")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
