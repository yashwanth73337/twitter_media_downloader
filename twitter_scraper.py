import asyncio
import json
import os
import calendar
import random
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
USER_DATA_DIR = "./twitter_profile" 
THRESHOLD_COUNT = 800  # < 800 uses Fast Mode, > 800 uses Deep Mode
# ---------------------

extracted_urls = set()
user_media_count = None  # Will store the detected count

def get_unique_filename(base_name):
    if not os.path.exists(base_name):
        return base_name
    name, ext = os.path.splitext(base_name)
    counter = 1
    while True:
        new_name = f"{name} ({counter}){ext}"
        if not os.path.exists(new_name):
            return new_name
        counter += 1

def save_link_live(filename, url):
    with open(filename, "a") as f:
        f.write(url + "\n")

# --- DATA EXTRACTION ---
async def handle_response(response, output_file):
    global user_media_count
    
    # 1. Capture User Stats (to get media count)
    if "UserByScreenName" in response.url and response.status == 200:
        try:
            data = await response.json()
            legacy = data['data']['user']['result']['legacy']
            user_media_count = legacy.get('media_count', 0)
            print(f"\n📊 DETECTED MEDIA COUNT: {user_media_count}")
        except:
            pass

    # 2. Capture Media Links
    if ("UserMedia" in response.url or "SearchTimeline" in response.url) and response.status == 200:
        try:
            data = await response.json()
            extract_media(data, output_file)
        except:
            pass

def extract_media(data, output_file):
    if isinstance(data, dict):
        if 'media_url_https' in data:
            url = data['media_url_https']
            if not url.endswith('.mp4'):
                clean_url = f"{url}?format=jpg&name=orig"
                if clean_url not in extracted_urls:
                    print(f"[IMAGE] {clean_url}")
                    extracted_urls.add(clean_url)
                    save_link_live(output_file, clean_url)
        
        if 'video_info' in data:
            variants = data['video_info'].get('variants', [])
            best_bitrate = 0
            best_url = None
            for v in variants:
                if v.get('content_type') == 'video/mp4':
                    bitrate = v.get('bitrate', 0)
                    if bitrate > best_bitrate:
                        best_bitrate = bitrate
                        best_url = v['url']
            if best_url and best_url not in extracted_urls:
                print(f"[VIDEO] {best_url}")
                extracted_urls.add(best_url)
                save_link_live(output_file, best_url)

        for value in data.values():
            extract_media(value, output_file)
    elif isinstance(data, list):
        for item in data:
            extract_media(item, output_file)

# --- STRATEGY 1: FAST SCROLL (< 800) ---
async def run_fast_scroll_mode(page):
    print("\n🚀 ACTIVATING FAST SCROLL MODE")
    print("(Just scrolling down until we hit the bottom...)")
    
    last_count = 0
    no_new_data_strikes = 0
    
    while True:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(4)
        
        current_count = len(extracted_urls)
        print(f"   Items found: {current_count}")
        
        if current_count == last_count:
            no_new_data_strikes += 1
            if no_new_data_strikes >= 3:
                print("   -> Jiggling page...")
                await page.evaluate("window.scrollBy(0, -500)")
                await asyncio.sleep(1)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            if no_new_data_strikes >= 5:
                print("   -> Reached bottom. Stopping.")
                break
        else:
            no_new_data_strikes = 0
            
        last_count = current_count

# --- STRATEGY 2: DEEP DRILL (> 800) ---
async def check_status(page):
    # FIXED: Added .first to avoid strict mode errors if multiple error messages appear
    if await page.get_by_text("No results for").first.is_visible(): return "empty"
    
    if await page.get_by_text("Something went wrong").first.is_visible() or \
       await page.get_by_text("Try again").first.is_visible(): 
        return "crash"
        
    return "ok"

async def scrape_month(page, username, year, month):
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day}"
    
    print(f"\n>>> DRILLING: {year}-{month:02d} <<<")
    
    search_query = f"from:{username} filter:media since:{start_date} until:{end_date}"
    encoded_query = search_query.replace(" ", "%20").replace(":", "%3A")
    url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=live"
    
    await page.goto(url, timeout=60000)
    await asyncio.sleep(random.uniform(4, 6))
    
    status = await check_status(page)
    if status == "empty":
        print("   -> Empty month. Skipping.")
        return 
    if status == "crash":
        print("   !!! CRASH DETECTED. Cooling down 60s...")
        await asyncio.sleep(60)
        await page.reload()
        await asyncio.sleep(10)
        if await check_status(page) == "empty": return

    last_count = len(extracted_urls)
    no_new_data_strikes = 0
    
    while True:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(random.uniform(3, 5))
        
        status = await check_status(page)
        if status == "crash":
             print("   -> Crash during scroll. Reloading...")
             await page.reload()
             await asyncio.sleep(10)
             continue
        if status == "empty": break

        current_count = len(extracted_urls)
        if current_count == last_count:
            no_new_data_strikes += 1
            print(f"   ...loading? ({no_new_data_strikes}/4)")
            if no_new_data_strikes >= 2:
                await page.evaluate("window.scrollBy(0, -400)")
                await asyncio.sleep(1)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            if no_new_data_strikes >= 4:
                print(f"   Finished {year}-{month:02d}.")
                break
        else:
            no_new_data_strikes = 0
            print(f"   Found: {current_count} (Total)")
        last_count = current_count

async def run_deep_drill_mode(page, username):
    print("\n🕵️ ACTIVATING DEEP DRILL MODE (Month-by-Month)")
    print("This account is huge. We need to scrape by date.")
    
    try:
        start_year = int(input("Enter Start Year (Oldest, e.g. 2009): "))
        end_year = int(input("Enter End Year (Newest, e.g. 2025): "))
    except ValueError:
        print("Invalid year. Defaulting to 2020-2025")
        start_year = 2020
        end_year = 2025

    for year in range(end_year, start_year - 1, -1):
        for month in range(12, 0, -1):
            await scrape_month(page, username, year, month)

# --- MAIN CONTROLLER ---
async def main():
    target_username = input("Enter username (e.g. tarak9999): ").strip().replace("@", "")
    
    # Generate unique filename immediately
    base_filename = f"{target_username}_full_links.txt"
    output_filename = get_unique_filename(base_filename)
    print(f"✅ Saving links to: {output_filename}")
    
    async with async_playwright() as p:
        print("--- LAUNCHING BROWSER ---")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            viewport={"width": 1280, "height": 720}
        )
        page = context.pages[0]
        page.on("response", lambda response: handle_response(response, output_filename))

        # 1. Go to Profile to check Media Count
        print("--- CHECKING PROFILE STATS ---")
        await page.goto(f"https://x.com/{target_username}", timeout=60000)
        await asyncio.sleep(5)
        
        # Check login
        if "login" in page.url:
            print("Please log in manually!")
            await asyncio.to_thread(input, "Press Enter after login...")
            # Reload to get stats
            await page.goto(f"https://x.com/{target_username}")
            await asyncio.sleep(5)

        # 2. DECISION LOGIC
        global user_media_count
        
        # Fallback if API didn't catch it (sometimes happens)
        if user_media_count is None:
            print("⚠️ Could not auto-detect media count.")
            user_input = input("Do you think this account has > 800 media files? (y/n): ").lower()
            if user_input == 'y':
                user_media_count = 9999
            else:
                user_media_count = 100

        # 3. EXECUTE STRATEGY
        if user_media_count < THRESHOLD_COUNT:
            # --- FAST MODE ---
            await page.goto(f"https://x.com/{target_username}/media")
            await asyncio.sleep(3)
            await run_fast_scroll_mode(page)
        else:
            # --- DEEP MODE ---
            await run_deep_drill_mode(page, target_username)

        print(f"\n--- MISSION COMPLETE ---")
        print(f"Total links saved: {len(extracted_urls)}")
        print(f"File: {output_filename}")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())