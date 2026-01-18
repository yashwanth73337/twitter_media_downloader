
# X (Twitter) Hybrid Scraper & Downloader 🚀

A powerful, "stealth-mode" tool to scrape and download high-quality images and videos from X (Twitter) accounts.

It uses a **Hybrid Strategy** to automatically handle both small accounts (Fast Scroll) and massive accounts with 12k+ media (Deep Drill Month-by-Month).

## 📂 The Files

* **`twitter_scraper.py`**: The "Hybrid Master" Scraper.
    * **Smart Detection:** Automatically detects if an account is huge (>800 media).
    * **Fast Mode:** Rapid scrolling for small accounts.
    * **Deep Mode:** Scrapes month-by-month for massive accounts to bypass infinite scroll limits.
    * **Crash Recovery:** Pauses and reloads if X shows "Something went wrong".

* **`media_downloader.py`**: The "Turbo Resilient" Downloader.
    * **Multi-threaded:** Downloads 5 files at once for maximum speed.
    * **Smart Resume:** Checks if a file exists before downloading (skips duplicates).
    * **404 Rescue:** Automatically switches to PNG format if a JPG link fails.
    * **Failure Logging:** Saves unrecoverable links (like 403 Forbidden ads) to `failed_downloads.txt`.

* **`requirements.txt`**: A list of the Python libraries needed to run this tool.

## ⚙️ Setup Instructions

1.  **Install Python** (if not already installed).

2.  **Install the required libraries:**
    Open your terminal or command prompt and run this command. It reads `requirements.txt` and installs the correct tools automatically:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install the browser engine:**
    This tool uses a real browser (Chromium) to browse X. Install it by running:
    ```bash
    playwright install chromium
    ```

## 🏃‍♂️ How to Use

### Step 1: Get the Links
Run the scraper script:
```bash
python3 twitter_scraper.py

```

1. Enter the **Username** (e.g., `tarak9999`).
2. A browser window will open. **Log in to X manually** if asked.
3. The bot will detect the media count:
* **Small Account:** It will scroll down quickly.
* **Huge Account:** It will ask for a **Start Year** and **End Year** (e.g., 2022 to 2025).


4. It will save all links to a text file (e.g., `tarak9999_full_links.txt`).

### Step 2: Download the Media

Run the downloader script:

```bash
python3 media_downloader.py

```

1. It will look for any `_links.txt` files in the folder.
2. Type the number of the file you want to download.
3. All images and videos will be saved in a new folder named after the user.

## ⚠️ Notes & Troubleshooting

* **Safety:** The script uses a persistent browser context (stored in a `twitter_profile` folder) so you only have to log in once. 
* **403 Forbidden Errors:** Some "Amplify" (Publisher/Ad) videos have strict security tokens and cannot be downloaded by scripts. These will be logged in `failed_downloads.txt`.
* **Rate Limits:** If you scrape too fast, X may pause the connection. The script handles this by waiting 60s and reloading automatically.

## ⚖️ Disclaimer

This tool is for educational purposes only. Please respect X's Terms of Service and do not use this tool for unauthorized data harvesting.
