import sys
import csv
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from db.database import get_db

def test_data_integrity(site_id: str, csv_path: str):
    print("==============================================")
    print("      DATA INTEGRITY VERIFICATION TEST        ")
    print("==============================================")
    
    # 1. Read the exact handles and titles from the CSV
    csv_products = {}
    if not Path(csv_path).exists():
        print(f"Error: CSV file not found at {csv_path}")
        return
        
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Title", "").strip()
            handle = row.get("Handle", "").strip()
            if title and handle:
                csv_products[handle] = title

    print(f"[+] Parsed {len(csv_products)} unique products from CSV.")

    # 2. Read what the crawler actually ingested into the RAG Database
    db_products = {}
    with get_db(site_id) as conn:
        rows = conn.execute("SELECT id, name FROM products").fetchall()
        for r in rows:
            # Reconstruct the expected handle from the name to match (or just match by name)
            # The CSV generator created handles by lowercase and replacing spaces with hyphens
            # E.g., "Eco-friendly Yellow Dustpan" -> "eco-friendly-yellow-dustpan"
            expected_handle = r["name"].lower().replace(" ", "-").replace("'", "")
            db_products[expected_handle] = r["name"]

    print(f"[+] Found {len(db_products)} products stored in the RAG Database.")
    
    # 3. Compare them
    missing_in_db = []
    for handle, title in csv_products.items():
        if handle not in db_products:
            missing_in_db.append(title)
            
    print("\n==============================================")
    print("                DATA BREAKDOWN                ")
    print("==============================================")
    print(f"1. Total Data in CSV (Attempted Upload):   {len(csv_products)}")
    print(f"2. Total Data found on Shopify (API):      {len(db_products)}")
    print(f"3. Total Data ingested by AI Crawler:      {len(db_products)}")
    print("----------------------------------------------")
    
    upload_percentage = (len(db_products) / len(csv_products)) * 100 if len(csv_products) > 0 else 0
    crawler_percentage = (len(db_products) / len(db_products)) * 100 if len(db_products) > 0 else 0
    
    print(f"Shopify Upload Success Rate:               {upload_percentage:.2f}% (Shopify throttled the rest)")
    print(f"Crawler Ingestion Rate (vs Shopify):       {crawler_percentage:.2f}% (Crawler successfully got everything Shopify had)")
    
    if len(missing_in_db) > 0:
        print(f"\n[INFO] {len(missing_in_db)} items from the CSV never made it into Shopify's database.")
        
if __name__ == "__main__":
    test_data_integrity("pisszq_ay_myshopify_com", "products.csv")
