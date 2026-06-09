import csv
import random

# 100 common everyday items categorized
items = {
    "Personal Care": [
        "Toothbrush", "Toothpaste", "Bar Soap", "Shampoo", "Conditioner", "Bath Towel", 
        "Toilet Paper", "Facial Tissues", "Deodorant", "Razor", "Shaving Cream", "Body Lotion", 
        "Lip Balm", "Hairbrush", "Comb", "Dental Floss", "Cotton Swabs", "Face Wash", 
        "Body Wash", "Hand Sanitizer", "Sunscreen", "Nail Clippers", "Tweezers"
    ],
    "Cleaning & Household": [
        "Sponge", "Dish Soap", "Laundry Detergent", "Trash Bags", "Paper Towels", 
        "Broom", "Dustpan", "Mop", "Bucket", "Trash Can", "Laundry Basket", 
        "Hangers", "Iron", "Ironing Board"
    ],
    "Electronics & Tech": [
        "Light Bulb", "AA Batteries", "Extension Cord", "Phone Charger", "Wireless Earbuds", 
        "Phone Case", "Screen Protector", "USB Cable", "Power Bank", "Smart Plug"
    ],
    "Office & Stationary": [
        "Ballpoint Pen", "Pencil", "Spiral Notebook", "Sticky Notes", "Scissors", 
        "Clear Tape", "Stapler", "Paper Clips", "Highlighter", "Eraser"
    ],
    "Apparel & Accessories": [
        "Backpack", "Umbrella", "Leather Wallet", "Sunglasses", "Wrist Watch", 
        "Leather Belt", "Cotton Socks", "Cotton Underwear", "Basic T-Shirt", "Denim Jeans", 
        "Winter Jacket", "Running Shoes", "Casual Sneakers", "House Slippers", "Pajama Set", "Scarf"
    ],
    "Kitchen & Dining": [
        "Coffee Mug", "Water Bottle", "Dinner Plate", "Soup Bowl", "Dining Fork", 
        "Butter Knife", "Soup Spoon", "Frying Pan", "Cooking Pot", "Silicone Spatula", 
        "Cutting Board", "Food Storage Container", "Can Opener", "Measuring Cups", 
        "Oven Mitt", "Pop-up Toaster", "Coffee Maker", "Blender"
    ],
    "Home & Bedroom": [
        "Bed Pillow", "Throw Blanket", "Bed Sheets", "Desk Lamp", "Area Rug", 
        "Blackout Curtains", "Wall Clock", "Picture Frame", "Scented Candle", "Cushion"
    ],
    "Health & Safety": [
        "First Aid Kit", "Band-Aids", "Pain Reliever", "Daily Vitamins", "Face Mask", 
        "Digital Thermometer"
    ]
}

qualities = ["Premium", "Basic", "Essential", "Eco-friendly", "Luxury", "Pro", "Classic", "Modern", "Vintage", "Minimalist", "Durable", "Ultra", "Everyday", "Smart"]
colors = ["Black", "White", "Red", "Blue", "Green", "Yellow", "Orange", "Purple", "Pink", "Brown", "Gray", "Silver", "Gold", "Navy"]

images = {
    "Personal Care": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571",
    "Cleaning & Household": "https://images.unsplash.com/photo-1584820927498-cafe2c111059",
    "Electronics & Tech": "https://images.unsplash.com/photo-1498049794561-7780e7231661",
    "Office & Stationary": "https://images.unsplash.com/photo-1497032628192-86f99bcd76bc",
    "Apparel & Accessories": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab",
    "Kitchen & Dining": "https://images.unsplash.com/photo-1556910103-1c02745a872f",
    "Home & Bedroom": "https://images.unsplash.com/photo-1513694203232-719a280e022f",
    "Health & Safety": "https://images.unsplash.com/photo-1583947215259-38e31be8751f"
}

headers = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Type", "Tags", "Published", 
    "Option1 Name", "Option1 Value", "Variant SKU", "Variant Grams", "Variant Inventory Tracker", 
    "Variant Inventory Qty", "Variant Inventory Policy", "Variant Fulfillment Service", 
    "Variant Price", "Variant Compare At Price", "Variant Requires Shipping", "Variant Taxable", "Image Src"
]

# Generate unique combinations
generated_handles = set()
products = []

target_count = 5000

while len(products) < target_count:
    category = random.choice(list(items.keys()))
    base_item = random.choice(items[category])
    quality = random.choice(qualities)
    color = random.choice(colors)
    
    title = f"{quality} {color} {base_item}"
    handle = title.lower().replace(" ", "-")
    
    if handle in generated_handles:
        continue
        
    generated_handles.add(handle)
    
    price = round(random.uniform(5.0, 150.0), 2)
    compare_at = round(price * 1.2, 2) if random.random() > 0.5 else ""
    qty = random.randint(10, 500)
    image_url = images[category] + f"?random={random.randint(1, 1000)}"
    
    product = {
        "Handle": handle,
        "Title": title,
        "Body (HTML)": f"<p>This is a highly reliable {title.lower()}, perfect for everyday human usage. Built with durability and practicality in mind to serve your daily needs.</p>",
        "Vendor": "AI Salesman Hub",
        "Type": base_item,
        "Tags": f"{category.lower().replace(' & ', ', ')}, {quality.lower()}, {color.lower()}",
        "Published": "TRUE",
        "Option1 Name": "Color",
        "Option1 Value": color,
        "Variant SKU": f"SKU-{random.randint(10000, 99999)}",
        "Variant Grams": random.choice([100, 250, 500, 1000]),
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": qty,
        "Variant Inventory Policy": "deny",
        "Variant Fulfillment Service": "manual",
        "Variant Price": price,
        "Variant Compare At Price": compare_at,
        "Variant Requires Shipping": "TRUE",
        "Variant Taxable": "TRUE",
        "Image Src": image_url
    }
    products.append(product)

with open("products.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(products)

print(f"Successfully generated products.csv with {len(products)} everyday products.")
