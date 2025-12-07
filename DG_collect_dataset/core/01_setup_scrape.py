import os
import time
import requests
import re
import utils
from pathlib import Path

# Fallback headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def download_image(url, save_path):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception:
        pass
    return False

def scrape_bing(query, limit, save_dir):
    print(f"--> Searching Bing for: '{query}'")
    search_url = f"https://www.bing.com/images/async?q={query}&first=0&count={limit}&adlt=off"
    
    try:
        html = requests.get(search_url, headers=HEADERS).text
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # Regex to find image URLs in Bing's async response
    # specific to murl (media url)
    links = re.findall(r'murl&quot;:&quot;(.*?)&quot;', html)
    
    print(f"--> Found {len(links)} potential links. Downloading {limit}...")
    
    count = 0
    for link in links:
        if count >= limit:
            break
            
        ext = 'jpg'
        if '.png' in link: ext = 'png'
        if '.jpeg' in link: ext = 'jpeg'
        
        filename = f"img_{count:04d}.{ext}"
        save_path = save_dir / filename
        
        if download_image(link, save_path):
            print(f"    Downloaded: {filename}")
            count += 1
        else:
            print(f"    Failed: {link[:30]}...")
            
    print(f"✅ Downloaded {count} images.")

def run(prompt, count, slug):
    path = utils.get_project_path(slug)
    
    # CORRECT KEY: 'scraped'
    scrape_dir = path / utils.DIRS['scraped']
    
    scrape_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we already have images
    existing = [f for f in os.listdir(scrape_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if len(existing) >= count:
        print(f"✅ Found {len(existing)} images in {scrape_dir}, skipping scrape.")
        return

    scrape_bing(prompt, count, scrape_dir)

if __name__ == "__main__":
    # Test standalone
    run("test search", 5, "test_slug")