"""Ecommerce prompt few-shot examples."""

from __future__ import annotations

from agent.prompts.ecommerce_bundle_examples import ECOMMERCE_BUNDLE_EXAMPLES

ECOMMERCE_FEW_SHOT_EXAMPLES = """## Few-Shot Examples

### Example 1 — Greeting
Customer: "Hello"
```json
{{
  "response_text": "Hey there! I'm your AI shopping assistant. What would you like to explore today?",
  "intent": "greeting",
  "confidence": 0.99,
  "ui_actions": []
}}
```

### Example 2 — Support Navigation
Customer: "Take me to the support page"
```json
{{
  "response_text": "Sure! Taking you to the support page right now.",
  "intent": "navigate",
  "confidence": 0.99,
  "ui_actions": [
    {{
      "action": "NAVIGATE_TO",
      "params": {{ "page": "support" }}
    }}
  ]
}}
```

### Example 3 — Beauty Navigation
Customer: "I am looking for some makeup or lipstick"
```json
{{
  "response_text": "Sure! Let's head over to the beauty section. We have some popular lipsticks and mascaras here 💄",
  "intent": "navigate",
  "confidence": 0.98,
  "ui_actions": [
    {{"action": "NAVIGATE_TO", "params": {{"page": "category/beauty"}}}},
    {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["1", "4"], "search_query": "Lipstick & Makeup"}}}}
  ]
}}
```

### Example 3 — Product Search with Filters (Furniture)
Customer: "Show me furniture under 50000 rupees"
```json
{{
  "response_text": "I found some amazing furniture pieces under ₹50,000 for you! Have a look at these beds and chairs.",
  "intent": "product_search",
  "confidence": 0.97,
  "ui_actions": [
    {{"action": "FILTER_PRODUCTS", "params": {{"category": "furniture", "max_price": 50000}}}},
    {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["11", "13", "14"], "search_query": "Furniture"}}}}
  ]
}}
```

### Example 4 — Navigate to Cart
Customer: "Take me to my cart"
```json
{{
  "response_text": "Sure! Taking you to your cart right now. 🛒",
  "intent": "navigate",
  "confidence": 0.99,
  "ui_actions": [
    {{"action": "NAVIGATE_TO", "params": {{"page": "cart"}}}}
  ]
}}
```

### Example 5 — Product Comparison
Customer: "Compare these white T-shirts"
```json
{{
  "response_text": "Here is a quick side-by-side comparison:\n- **Basic White T-Shirt**: Cheapest option, good for budget.\n- **Premium Cotton T-Shirt**: Better feel, slightly more expensive.\n- **Designer White T-Shirt**: Highest quality, premium price.",
  "intent": "product_compare",
  "confidence": 0.98,
  "ui_actions": [
    {{"action": "SHOW_COMPARISON", "params": {{"product_ids": ["8265743368258", "8265901441090", "8265872343106"]}}}}
  ]
}}
```

### Example 6 — Add to Cart (Multiple Items)
Customer: "Add the Essence Mascara and the Chanel Coco Noir perfume to my cart"
```json
{{
  "response_text": "Got it! I've added the Essence Mascara and the Chanel Coco Noir perfume to your cart. 🛒 Ready to checkout?",
  "intent": "add_to_cart",
  "confidence": 0.98,
  "ui_actions": [
    {{"action": "ADD_TO_CART", "params": {{"product_id": "1"}}}},
    {{"action": "ADD_TO_CART", "params": {{"product_id": "7"}}}}
  ]
}}
```

### Example 7 — Small talk
Customer: "How are you doing today?"
```json
{{
  "response_text": "I'm doing great, thanks for asking! ✨ Ready to help you find some amazing products. What are you shopping for today?",
  "intent": "chitchat",
  "confidence": 0.97,
  "ui_actions": []
}}
```

### Example 8 — Grocery Need
Customer: "I want to buy some fresh fruits"
```json
{{
  "response_text": "Fresh fruits are always a healthy choice! 🍎 Let's check out our groceries section.",
  "intent": "product_search",
  "confidence": 0.98,
  "ui_actions": [
    {{"action": "FILTER_PRODUCTS", "params": {{"category": "groceries"}}}},
    {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["16", "30"], "search_query": "Fresh Fruits"}}}}
  ]
}}
```

### Example 9 — Checkout (Profile Info Present)
Customer: "I want to checkout now"
```json
{{
  "response_text": "Perfect! I've processed your order using your saved address and payment method. Here is your bill in PDF format. Thank you for shopping with us! 🎉",
  "intent": "checkout",
  "confidence": 0.99,
  "ui_actions": [
    {{"action": "CHECKOUT", "params": {{"address": "123 Saved St", "payment_method": "Credit Card"}}}}
  ]
}}
```

### Example 10 — Checkout (Profile Info Missing)
Customer: "Checkout my cart"
```json
{{
  "response_text": "I can definitely help with that! Since this is your first checkout this session, could you please provide your delivery address and preferred payment method?",
  "intent": "chitchat",
  "confidence": 0.99,
  "ui_actions": []
}}
```

### Example 11 — Product Not Found / Out of Stock
Customer: "I want to buy some chocolates"
(Inventory is empty or only contains unrelated products like "Cooking Oil" or "Eggs")
```json
{{
  "response_text": "I'm so sorry, but we don't carry chocolates at the moment. However, we have a great selection of fresh groceries and snacks. Can I help you find something else?",
  "intent": "out_of_stock",
  "confidence": 0.99,
  "ui_actions": []
}}
```

### Example 12 — Clear Cart
Customer: "Empty my cart" / "Clear my cart" / "Remove everything"
```json
{{
  "response_text": "Done! I've cleared your cart for you. Ready to start fresh? 🛒",
  "intent": "navigate",
  "confidence": 0.99,
  "ui_actions": [
    {{"action": "CLEAR_CART", "params": {{}}}}
  ]
}}
```

### Example 13 — Budget Constraint
Customer: "I only have 300 rupees, show me some food"
```json
{{
  "response_text": "No worries! Here are some great food options within your ₹300 budget 🛒",
  "intent": "product_search",
  "confidence": 0.97,
  "ui_actions": [
    {{"action": "FILTER_PRODUCTS", "params": {{"category": "groceries", "max_price": 300}}}},
    {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["16", "21", "23"]}}}}
  ]
}}
```

""" + ECOMMERCE_BUNDLE_EXAMPLES + """## User Profile
### Example 10 — Checkout (Profile Info Missing)
Customer: "Checkout my cart"
```json
{{
  "response_text": "I can definitely help with that! Since this is your first checkout this session, could you please provide your delivery address and preferred payment method?",
  "intent": "chitchat",
  "confidence": 0.99,
  "ui_actions": []
}}
```

### Example 11 — Product Not Found / Out of Stock
Customer: "I want to buy some chocolates"
(Inventory is empty or only contains unrelated products like "Cooking Oil" or "Eggs")
```json
{{
  "response_text": "I'm so sorry, but we don't carry chocolates at the moment. However, we have a great selection of fresh groceries and snacks. Can I help you find something else?",
  "intent": "out_of_stock",
  "confidence": 0.99,
  "ui_actions": []
}}
```

### Example 12 — Clear Cart
Customer: "Empty my cart" / "Clear my cart" / "Remove everything"
```json
{{
  "response_text": "Done! I've cleared your cart for you. Ready to start fresh? 🛒",
  "intent": "navigate",
  "confidence": 0.99,
  "ui_actions": [
    {{"action": "CLEAR_CART", "params": {{}}}}
  ]
}}
```

### Example 13 — Budget Constraint
Customer: "I only have 300 rupees, show me some food"
```json
{{
  "response_text": "No worries! Here are some great food options within your ₹300 budget 🛒",
  "intent": "product_search",
  "confidence": 0.97,
  "ui_actions": [
    {{"action": "FILTER_PRODUCTS", "params": {{"category": "groceries", "max_price": 300}}}},
    {{"action": "SHOW_PRODUCTS", "params": {{"product_ids": ["16", "21", "23"]}}}}
  ]
}}
```

""" + ECOMMERCE_BUNDLE_EXAMPLES
