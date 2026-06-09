import sys
import os
import httpx
from pathlib import Path

# Add project root to sys.path so we can import config & db
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

import config
from db.database import get_global_db

def inject_script(shop_domain: str):
    # 1. Retrieve the access token from the database
    access_token = None
    with get_global_db() as conn:
        result = conn.execute(
            "SELECT access_token FROM shopify_installations WHERE shop_domain = %s",
            (shop_domain,)
        ).fetchone()
        if result:
            access_token = result["access_token"]
            
    if not access_token:
        print(f"❌ Error: No access token found for store '{shop_domain}'. Is the app installed?")
        sys.exit(1)

    # 2. Define the ScriptTag payload
    script_url = f"{config.PUBLIC_API_URL}/shopbot.js"
    
    payload = {
        "script_tag": {
            "event": "onload",
            "src": script_url,
            "display_scope": "online_store"
        }
    }

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    endpoint = f"https://{shop_domain}/admin/api/2024-01/script_tags.json"

    print(f"Injecting script {script_url} into {shop_domain}...")
    
    # 3. Make the API request
    with httpx.Client() as client:
        # First check if it already exists to avoid duplicates
        res = client.get(endpoint, headers=headers)
        if res.status_code == 200:
            existing_tags = res.json().get("script_tags", [])
            for tag in existing_tags:
                if "shopbot.js" in tag.get("src", ""):
                    print(f"[!] Script tag already exists! Updating it...")
                    client.delete(f"{endpoint.replace('.json', '')}/{tag['id']}.json", headers=headers)

        # Create the new ScriptTag
        response = client.post(endpoint, json=payload, headers=headers)
        
        if response.status_code == 201:
            print("[SUCCESS] Successfully injected Voice AI Widget into the storefront!")
        else:
            print(f"[ERROR] Failed to inject script. Status code: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inject_widget.py <shop_domain>")
        sys.exit(1)
        
    inject_script(sys.argv[1])
