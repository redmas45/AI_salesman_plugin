import json
from pathlib import Path

# Paths
PLUGIN_DIR = Path(__file__).parent.parent.resolve()
VERCEL_DIR = PLUGIN_DIR.parent / "Vercel_website"
CRAWL_FILE = PLUGIN_DIR / "crawl.json"
SOURCE_FILE = VERCEL_DIR / "out" / "api" / "products.json"

def normalize_name(name):
    # Basic normalization to match slightly different titles
    return name.lower().replace("-", " ").strip()

def main():
    if not SOURCE_FILE.exists():
        print(f"❌ Could not find Vercel products file at: {SOURCE_FILE}")
        return
        
    if not CRAWL_FILE.exists():
        print(f"❌ Could not find crawl.json at: {CRAWL_FILE}")
        print("Make sure you restart the server (python run.py) first so it can generate the crawl.json file!")
        return

    # Load Source Products (Ground Truth)
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        source_data = json.load(f)
        source_products = source_data.get("products", [])
        
    # Load Crawled Products
    with open(CRAWL_FILE, "r", encoding="utf-8") as f:
        crawled_products = json.load(f)

    print("📊 Crawler Performance Evaluation")
    print("=" * 40)
    print(f"Ground Truth Items (Vercel API): {len(source_products)}")
    print(f"Crawled Items (AI Salesman):     {len(crawled_products)}")
    print("-" * 40)

    # Build dictionaries by normalized name
    source_dict = {normalize_name(p["name"]): p for p in source_products}
    crawled_dict = {normalize_name(p["name"]): p for p in crawled_products}

    # Analyze matches
    matched = 0
    missing = []
    
    for name, src_product in source_dict.items():
        if name in crawled_dict:
            matched += 1
        else:
            # Try to see if it's partially matched
            partial_match = any(name in c_name or c_name in name for c_name in crawled_dict.keys())
            if partial_match:
                matched += 1
            else:
                missing.append(src_product["name"])
                
    extra = []
    for name, crw_product in crawled_dict.items():
        if name not in source_dict:
            # Check for partial match to avoid false "extras"
            if not any(name in s_name or s_name in name for s_name in source_dict.keys()):
                extra.append(crw_product["name"])

    # Calculate metrics
    recall = (matched / len(source_products)) * 100 if source_products else 0
    precision = (matched / len(crawled_products)) * 100 if crawled_products else 0

    print(f"✅ Successfully Matched: {matched}")
    print(f"⚠️ Missing Items:      {len(missing)}")
    print(f"❓ Extra Items Crawled: {len(extra)}")
    print("-" * 40)
    print(f"🎯 Recall:    {recall:.1f}% (Did we find everything?)")
    print(f"🎯 Precision: {precision:.1f}% (Is everything we found actually a product?)")
    
    if missing:
        print("\n❌ Missing Products:")
        for m in missing:
            print(f"  - {m}")
            
    if extra:
        print("\n❓ Extra Products Found (Could be valid related items or noise):")
        for e in extra[:10]:
            print(f"  - {e}")
        if len(extra) > 10:
            print(f"  - ... and {len(extra) - 10} more.")

if __name__ == "__main__":
    main()
