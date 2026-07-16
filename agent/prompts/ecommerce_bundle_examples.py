"""Bundle-focused ecommerce prompt examples."""

from __future__ import annotations

ECOMMERCE_BUNDLE_EXAMPLES = """### Example 14 — Bundle Request (Camping Trip)
Customer: "I want to pack things for my camping trip, I have a budget of 3000"
```json
{{
  "response_text": "I've put together a fun camping bundle for you! I found a sturdy tent, a flashlight, and some trail mix. The total comes to around ₹2,500, well under your budget! Shall I add these to your cart?",
  "intent": "product_search",
  "confidence": 0.98,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["15", "21", "34"]}}}}
  ]
}}
```

### Example 15 — Bundle Request (Makeup Kit)
Customer: "Help me build a makeup kit under 5k"
```json
{{
  "response_text": "I can definitely help with that! Here is a great starter kit with foundation, lipstick, and mascara for under ₹5,000. Would you like me to add this bundle to your cart?",
  "intent": "product_search",
  "confidence": 0.98,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["2", "4", "8"]}}}}
  ]
}}
```

### Example 16 — Bundle Request (Skincare Routine)
Customer: "I need a full skincare routine for under 4000 rupees"
```json
{{
  "response_text": "I've curated a beautiful skincare routine for you, including a cleanser, toner, and moisturizer. The combined total is ₹3,800. Let me know if you want me to add these to your cart!",
  "intent": "product_search",
  "confidence": 0.97,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["11", "12", "19"]}}}}
  ]
}}
```

### Example 17 — Bundle Request (Home Office)
Customer: "Can you get me a desk and a chair for my home office? Budget is 20k"
```json
{{
  "response_text": "Here is a sleek wooden desk and an ergonomic chair that fit perfectly within your ₹20,000 budget! Do these look good? Shall I pop them into your cart?",
  "intent": "product_search",
  "confidence": 0.98,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["45", "46"]}}}}
  ]
}}
```

### Example 18 — Bundle Request (Gaming Setup)
Customer: "I'm setting up a gaming station, I need a headset and mouse under 8000"
```json
{{
  "response_text": "Awesome! I found a great gaming headset and an RGB mouse that total just under ₹8,000. Would you like me to add this gaming bundle to your cart?",
  "intent": "product_search",
  "confidence": 0.96,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["51", "53"]}}}}
  ]
}}
```

### Example 19 — Bundle Request (Living Room Upgrade)
Customer: "I have 50k, I want to upgrade my living room with a sofa and a rug"
```json
{{
  "response_text": "I've picked out a gorgeous sofa and a matching rug that fit comfortably inside your ₹50,000 budget! Would you like me to add them to your cart?",
  "intent": "product_search",
  "confidence": 0.97,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["61", "65"]}}}}
  ]
}}
```

### Example 20 — Bundle Request (Monthly Groceries)
Customer: "Get me rice, dal, and oil. Try to keep it under 1500"
```json
{{
  "response_text": "I've found a bundle with premium basmati rice, dal, and cooking oil for just under ₹1,500. Should I add these essentials to your cart?",
  "intent": "product_search",
  "confidence": 0.98,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["20", "22", "25"]}}}}
  ]
}}
```

### Example 21 — Bundle Request (Summer Wardrobe)
Customer: "I need 2 summer dresses, budget is 3000"
```json
{{
  "response_text": "Here are two beautiful summer dresses I found! Their combined price is under your ₹3,000 budget. Let me know if you'd like me to add them to your cart!",
  "intent": "product_search",
  "confidence": 0.95,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["81", "82"]}}}}
  ]
}}
```

### Example 22 — Bundle Request (Party Snacks)
Customer: "I'm hosting a party, get me some chips and cold drinks for 500 rupees"
```json
{{
  "response_text": "Party time! 🥳 I've selected some popular chips and cold drinks that total under ₹500. Would you like me to add these snacks to your cart?",
  "intent": "product_search",
  "confidence": 0.98,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["31", "33"]}}}}
  ]
}}
```

### Example 23 — Bundle Request (Gift Box)
Customer: "I want to gift someone a perfume and a watch, I have 10k"
```json
{{
  "response_text": "What a lovely gift idea! I found a premium perfume and an elegant watch that together cost just under ₹10,000. Would you like me to add this gift bundle to your cart?",
  "intent": "product_search",
  "confidence": 0.97,
  "ui_actions": [
     {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["91", "95"]}}}}
  ]
}}
```

### Example 24 — Start Over
Customer: "You are not understanding me, let's start over"
```json
{{
  "response_text": "I'm so sorry for the confusion! I've cleared my memory. Let's start fresh — what can I help you find?",
  "intent": "chitchat",
  "confidence": 0.99,
  "ui_actions": [
    {{"action": "CLEAR_HISTORY", "params": {{}}}}
  ]
}}
```

"""
