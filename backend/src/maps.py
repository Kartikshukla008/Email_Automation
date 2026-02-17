import asyncio
import time
import csv
import json
import random
import hashlib
import os
from playwright.async_api import async_playwright

# ============================================
# COUNTRY/REGION DETECTION
# ============================================

COUNTRY_REGIONS = {
    # United States
    "united states": {"hl": "en", "gl": "us", "coords": {"lat": 37.0902, "lng": -95.7129}},
    "usa": {"hl": "en", "gl": "us", "coords": {"lat": 37.0902, "lng": -95.7129}},
    "california": {"hl": "en", "gl": "us", "coords": {"lat": 36.7783, "lng": -119.4179}},
    "new york": {"hl": "en", "gl": "us", "coords": {"lat": 42.1657, "lng": -74.9481}},
    "texas": {"hl": "en", "gl": "us", "coords": {"lat": 31.9686, "lng": -99.9018}},
    "florida": {"hl": "en", "gl": "us", "coords": {"lat": 27.6648, "lng": -81.5158}},
    "illinois": {"hl": "en", "gl": "us", "coords": {"lat": 40.6331, "lng": -89.3985}},
    
    # India
    "india": {"hl": "en", "gl": "in", "coords": {"lat": 20.5937, "lng": 78.9629}},
    "delhi": {"hl": "en", "gl": "in", "coords": {"lat": 28.7041, "lng": 77.1025}},
    "mumbai": {"hl": "en", "gl": "in", "coords": {"lat": 19.0760, "lng": 72.8777}},
    "bangalore": {"hl": "en", "gl": "in", "coords": {"lat": 12.9716, "lng": 77.5946}},
    "chandigarh": {"hl": "en", "gl": "in", "coords": {"lat": 30.7333, "lng": 76.7794}},
    "pune": {"hl": "en", "gl": "in", "coords": {"lat": 18.5204, "lng": 73.8567}},
    
    # United Kingdom
    "united kingdom": {"hl": "en", "gl": "uk", "coords": {"lat": 55.3781, "lng": -3.4360}},
    "uk": {"hl": "en", "gl": "uk", "coords": {"lat": 55.3781, "lng": -3.4360}},
    "london": {"hl": "en", "gl": "uk", "coords": {"lat": 51.5074, "lng": -0.1278}},
    "manchester": {"hl": "en", "gl": "uk", "coords": {"lat": 53.4808, "lng": -2.2426}},
    
    # Canada
    "canada": {"hl": "en", "gl": "ca", "coords": {"lat": 56.1304, "lng": -106.3468}},
    "toronto": {"hl": "en", "gl": "ca", "coords": {"lat": 43.6532, "lng": -79.3832}},
    "vancouver": {"hl": "en", "gl": "ca", "coords": {"lat": 49.2827, "lng": -123.1207}},
    
    # Australia
    "australia": {"hl": "en", "gl": "au", "coords": {"lat": -25.2744, "lng": 133.7751}},
    "sydney": {"hl": "en", "gl": "au", "coords": {"lat": -33.8688, "lng": 151.2093}},
    "melbourne": {"hl": "en", "gl": "au", "coords": {"lat": -37.8136, "lng": 144.9631}},
    
    # Germany
    "germany": {"hl": "de", "gl": "de", "coords": {"lat": 51.1657, "lng": 10.4515}},
    "berlin": {"hl": "de", "gl": "de", "coords": {"lat": 52.5200, "lng": 13.4050}},
    "munich": {"hl": "de", "gl": "de", "coords": {"lat": 48.1351, "lng": 11.5820}},
    
    # France
    "france": {"hl": "fr", "gl": "fr", "coords": {"lat": 46.2276, "lng": 2.2137}},
    "paris": {"hl": "fr", "gl": "fr", "coords": {"lat": 48.8566, "lng": 2.3522}},
    
    # Spain
    "spain": {"hl": "es", "gl": "es", "coords": {"lat": 40.4637, "lng": -3.7492}},
    "madrid": {"hl": "es", "gl": "es", "coords": {"lat": 40.4168, "lng": -3.7038}},
    "barcelona": {"hl": "es", "gl": "es", "coords": {"lat": 41.3851, "lng": 2.1734}},
    
    # Italy
    "italy": {"hl": "it", "gl": "it", "coords": {"lat": 41.8719, "lng": 12.5674}},
    "rome": {"hl": "it", "gl": "it", "coords": {"lat": 41.9028, "lng": 12.4964}},
    "milan": {"hl": "it", "gl": "it", "coords": {"lat": 45.4642, "lng": 9.1900}},
    
    # Japan
    "japan": {"hl": "ja", "gl": "jp", "coords": {"lat": 36.2048, "lng": 138.2529}},
    "tokyo": {"hl": "ja", "gl": "jp", "coords": {"lat": 35.6762, "lng": 139.6503}},
    "osaka": {"hl": "ja", "gl": "jp", "coords": {"lat": 34.6937, "lng": 135.5023}},
    
    # China
    "china": {"hl": "zh-CN", "gl": "cn", "coords": {"lat": 35.8617, "lng": 104.1954}},
    "beijing": {"hl": "zh-CN", "gl": "cn", "coords": {"lat": 39.9042, "lng": 116.4074}},
    "shanghai": {"hl": "zh-CN", "gl": "cn", "coords": {"lat": 31.2304, "lng": 121.4737}},
    
    # Brazil
    "brazil": {"hl": "pt", "gl": "br", "coords": {"lat": -14.2350, "lng": -51.9253}},
    "sao paulo": {"hl": "pt", "gl": "br", "coords": {"lat": -23.5505, "lng": -46.6333}},
    "rio de janeiro": {"hl": "pt", "gl": "br", "coords": {"lat": -22.9068, "lng": -43.1729}},
    
    # Mexico
    "mexico": {"hl": "es", "gl": "mx", "coords": {"lat": 23.6345, "lng": -102.5528}},
    "mexico city": {"hl": "es", "gl": "mx", "coords": {"lat": 19.4326, "lng": -99.1332}},
    
    # Singapore
    "singapore": {"hl": "en", "gl": "sg", "coords": {"lat": 1.3521, "lng": 103.8198}},
    
    # UAE
    "uae": {"hl": "en", "gl": "ae", "coords": {"lat": 23.4241, "lng": 53.8478}},
    "dubai": {"hl": "en", "gl": "ae", "coords": {"lat": 25.2048, "lng": 55.2708}},
    
    # Default fallback
    "default": {"hl": "en", "gl": "us", "coords": {"lat": 37.0902, "lng": -95.7129}}
}


def detect_country_from_query(query: str):
    """
    Auto-detect country/region from query and return hl, gl, and coordinates
    """
    query_lower = query.lower()
    
    # Check for matches in query
    for region, config in COUNTRY_REGIONS.items():
        if region in query_lower:
            return config
    
    return COUNTRY_REGIONS["default"]


# ============================================
# SHARED UTILITIES
# ============================================

def generate_fingerprint():
    """Generate a unique browser fingerprint"""
    timestamp = str(time.time())
    random_str = str(random.randint(100000, 999999))
    fingerprint = hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest()
    return fingerprint


def generate_session_id():
    """Generate a unique session ID"""
    timestamp = str(time.time())
    random_str = str(random.randint(1000000, 9999999))
    session_id = hashlib.sha256(f"{timestamp}{random_str}".encode()).hexdigest()[:16]
    return session_id


def get_random_user_agent():
    """Return a random realistic user agent"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    return random.choice(user_agents)


async def save_cookies(context, filename="cookies.json"):
    """Save cookies to file"""
    try:
        cookies = await context.cookies()
        # Ensure directory exists or text file logic
        # For simplicity, we skip if we face path issues
        with open(filename, "w") as f:
            json.dump(cookies, f, indent=2)
    except:
        pass


async def load_cookies(context, filename="cookies.json"):
    """Load cookies from file"""
    try:
        with open(filename, "r") as f:
            cookies = json.load(f)
            await context.add_cookies(cookies)
        return True
    except FileNotFoundError:
        return False


# ============================================
# MAIN SCRAPER LOGIC
# ============================================

async def scrape_google_maps_task(query: str, target_results: int, output_file: str):
    """
    Scrape Google Maps and save results to CSV.
    This function is designed to run as a background task.
    """
    
    # Auto-detect country/region from query
    region_config = detect_country_from_query(query)
    hl = region_config["hl"]  # Language
    gl = region_config["gl"]  # Country
    coords = region_config["coords"]
    
    session_id = generate_session_id()
    fingerprint = generate_fingerprint()
    user_agent = get_random_user_agent()
    
    # Create CSV file with headers
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Website"])
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        try:
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080},
                locale=f'{hl}-{gl.upper()}',
                timezone_id='America/Los_Angeles' if gl == 'us' else 'Asia/Kolkata',
                permissions=['geolocation'],
                geolocation={'latitude': coords['lat'], 'longitude': coords['lng']},
                extra_http_headers={
                    'Accept-Language': f'{hl}-{gl.upper()},{hl};q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'X-Session-ID': session_id,
                    'X-Browser-Fingerprint': fingerprint
                }
            )
            
            page = await context.new_page()
            
            # Stealth scripts
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Build Google Maps URL
            maps_url = f"https://www.google.com/maps?hl={hl}&gl={gl}"
            
            try:
                print(f"[MAPS] Navigating to {maps_url}")
                await page.goto(maps_url, timeout=60000)
                
                # Handle "Accept Cookies" consent form typical in EU/certain regions
                # Look for common consent buttons
                try:
                    consent_button = page.locator('form[action*="consent.google.com"] button')
                    if await consent_button.count() > 0:
                        print("[MAPS] Accepting cookies...")
                        await consent_button.first.click()
                        await page.wait_for_load_state('networkidle')
                except Exception as e:
                    print(f"[MAPS] Cookie check warning: {e}")

            except Exception as e:
                print(f"[MAPS] Timeout loading initial map: {e}")
                return

            # Search
            try:
                print(f"[MAPS] Searching for '{query}'...")
                search_box = page.locator("input#searchboxinput")
                if await search_box.count() == 0:
                    # Fallback selectors
                    search_box = page.locator("input#ucc-1")
                    if await search_box.count() == 0:
                        search_box = page.locator("input[name='q']")
                
                await search_box.fill(query)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"[MAPS] Error during search: {e}")
                return

            # Check for results feed
            try:
                # Wait for the feed (sidebar list)
                # Try multiple selectors for the feed container
                feed_selector = 'div[role="feed"]'
                try:
                    await page.wait_for_selector(feed_selector, timeout=10000)
                except:
                    print("[MAPS] Warning: div[role='feed'] not found. Trying fallback...")
                    # Sometimes it might be different structure in mobile view or different A/B test
                    # Just check if we have any results
                    await page.wait_for_selector('a[href*="/maps/place"]', timeout=10000)
                    feed_selector = 'div[class*="m6QErb"][aria-label*="Results"]' 
                    # This class is often used but might change. 
                    # Better to stick to role="feed" or rely on finding specific items
            
            except:
                print("[MAPS] No results found or selector failed.")
                return
            
            print("[MAPS] Results found. Collecting URLs...")

            # STEP 1: Collect URLs by scrolling
            collected_urls = set()
            scroll_try = 0
            max_scroll_try = 20
            
            feed = page.locator('div[role="feed"]')
            if await feed.count() == 0:
                # Fallback: if role=feed isn't there, maybe scroll the window or finding the right container
                # We will try to find the container that has the results
                feed = page.locator('a[href*="/maps/place"]').first.locator('..').locator('..').locator('..')
            
            while len(collected_urls) < target_results and scroll_try < max_scroll_try:
                # Find all result links
                links = page.locator('a[href*="/maps/place"]')
                count = await links.count()
                
                for i in range(count):
                    url = await links.nth(i).get_attribute("href")
                    if url:
                        # Clean URL (remove tracking params if needed, but keeping full is safer for navigation)
                        collected_urls.add(url)
                
                if len(collected_urls) >= target_results:
                    break
                    
                # Scroll down
                # If feed element exists and is scrollable
                if await feed.count() > 0:
                    await feed.evaluate("el => el.scrollBy(0, 5000)")
                else:
                    await page.mouse.wheel(0, 5000)
                
                await asyncio.sleep(2)
                
                # Check if we are stuck (count didn't increase)
                new_count = await links.count()
                if new_count <= count and count > 0:
                    # End of list?
                    scroll_try += 1
                else:
                    scroll_try = 0  # Reset if we found new items

            print(f"[MAPS] Collected {len(collected_urls)} URLs. Starting scrape...")
            
            # STEP 2: Scrape each URL
            scraped_count = 0
            
            # Limit to target_results
            urls_to_scrape = list(collected_urls)[:target_results]
            
            for url in urls_to_scrape:
                try:
                    await page.goto(url, timeout=30000)
                    await page.wait_for_selector("h1", timeout=5000) # Wait for title
                    
                    # Extract Name
                    name_loc = page.locator("h1.DUwDvf")
                    if await name_loc.count() == 0:
                        name_loc = page.locator("h1")
                    
                    name = "N/A"
                    if await name_loc.count() > 0:
                        name = (await name_loc.first.text_content()).strip()
                    
                    # Extract Website
                    website = "N/A"
                    # Look for website button/link
                    # Common selectors: a[data-item-id="authority"], a[aria-label^="Website"]
                    web_loc = page.locator('a[data-item-id="authority"]')
                    if await web_loc.count() == 0:
                        web_loc = page.locator('a[aria-label*="Website"]')
                    
                    if await web_loc.count() > 0:
                        website = await web_loc.first.get_attribute("href") or "N/A"
                    
                    # Append to CSV
                    with open(output_file, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow([name, website])
                    
                    print(f"[MAPS] Scraped: {name} - {website}")
                    scraped_count += 1
                    
                    # Adding random delay to be human-like
                    await asyncio.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    print(f"[MAPS] Error scraping one item: {e}")
                    continue
                    
            print(f"[MAPS] Completed. Total successfully scraped: {scraped_count}")

        finally:
            await browser.close()
