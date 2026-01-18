import asyncio
import aiohttp
import os
import glob
from datetime import datetime

# --- CONFIGURATION ---
CONCURRENT_LIMIT = 5
MAX_RETRIES = 3
FAILURE_LOG_FILE = "failed_downloads.txt"
# ---------------------

def log_failure(url, reason):
    """Saves failed links to a text file for manual review"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(FAILURE_LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {reason}: {url}\n")

def get_unique_folder_name(base_name):
    if not os.path.exists(base_name):
        return base_name
    counter = 1
    while True:
        new_name = f"{base_name} ({counter})"
        if not os.path.exists(new_name):
            return new_name
        counter += 1

async def download_worker(session, queue, folder_name, total_files):
    while not queue.empty():
        index, url = await queue.get()
        
        # --- FILENAME LOGIC ---
        try:
            if "format=" in url: # Image
                raw_id = url.split("/")[4].split("?")[0]
                clean_id = raw_id.replace(".jpg", "").replace(".png", "")
                name = f"{clean_id}.jpg"
            else: # Video
                name = url.split("/")[-1].split("?")[0]
        except:
            name = f"file_{index}.dat"

        filepath = os.path.join(folder_name, name)
        percent = int((index / total_files) * 100)

        if os.path.exists(filepath):
            queue.task_done()
            continue

        # --- DOWNLOAD LOOP ---
        success = False
        current_url = url 

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=None, sock_read=30, sock_connect=15)
                async with session.get(current_url, timeout=timeout) as response:
                    
                    if response.status == 200:
                        data = await response.read()
                        with open(filepath, 'wb') as f:
                            f.write(data)
                        print(f"[{index}/{total_files}] {percent}% ✅ DONE: {name}")
                        success = True
                        break 
                    
                    elif response.status == 404:
                        if "format=jpg" in current_url:
                            print(f"[{index}/{total_files}] ⚠️ 404 on JPG. Trying PNG rescue...")
                            current_url = current_url.replace("format=jpg", "format=png")
                            continue 
                        else:
                            print(f"[{index}/{total_files}] ❌ 404 Not Found: {current_url}")
                            # Log immediate failure if 404
                            log_failure(current_url, "404 Not Found")
                            break 
                    
                    else:
                        await asyncio.sleep(1)

            except Exception as e:
                pass 
        
        # If it failed after all attempts and wasn't a 404 (which we already logged)
        if not success and not os.path.exists(filepath):
            if "format=png" not in current_url: # Don't double log 404s
                print(f"[{index}/{total_files}] 💀 FAILED: {name}")
                log_failure(url, "Download Failed")

        queue.task_done()

async def main():
    # --- UPDATED FILE DETECTION LOGIC ---
    files = glob.glob("*links*.txt")
    files.sort(key=os.path.getmtime)

    if not files:
        if os.path.exists("links.txt"):
            files = ["links.txt"]
        else:
            print("No link files found! Run scraper.py first.")
            return

    print("Found files:")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
    
    try:
        choice = int(input("Select file number: ")) - 1
        selected_file = files[choice]
    except:
        selected_file = files[-1]

    # Folder setup
    username = selected_file.replace(".txt", "").replace("_full_links", "").replace("_links", "").split(" (")[0]
    target_folder = get_unique_folder_name(username)
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    
    # Load Links
    with open(selected_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    total_files = len(urls)
    print(f"Downloading {total_files} files from '{selected_file}' to '{target_folder}'...")

    queue = asyncio.Queue()
    for i, url in enumerate(urls, 1):
        queue.put_nowait((i, url))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    connector = aiohttp.TCPConnector(limit=CONCURRENT_LIMIT)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [asyncio.create_task(download_worker(session, queue, target_folder, total_files)) for _ in range(CONCURRENT_LIMIT)]
        await queue.join()
        for task in tasks: task.cancel()

    print("\nDownload Complete!")
    if os.path.exists(FAILURE_LOG_FILE):
        print(f"⚠️ Check {FAILURE_LOG_FILE} for any failed links.")

if __name__ == "__main__":
    asyncio.run(main())