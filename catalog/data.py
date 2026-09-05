"""Dummy product catalog — 10 products across 4 categories."""

PRODUCTS = [
    # --- Groceries ---
    {
        "id": "prod_rice_basmati_5kg",
        "name": "Premium Basmati Rice 5kg",
        "price": 45000,  # ₹450
        "stock": 25,
        "description": "Aged long-grain basmati rice, perfect for biryanis and pulao. Sourced from the foothills of the Himalayas.",
        "category": "groceries",
    },
    {
        "id": "prod_toor_dal_1kg",
        "name": "Organic Toor Dal 1kg",
        "price": 18000,  # ₹180
        "stock": 40,
        "description": "Unpolished organic toor dal, high in protein. Cooks in 20 minutes. Ideal for everyday dal preparations.",
        "category": "groceries",
    },
    {
        "id": "prod_olive_oil_1l",
        "name": "Extra Virgin Olive Oil 1L",
        "price": 65000,  # ₹650
        "stock": 15,
        "description": "Cold-pressed extra virgin olive oil imported from Spain. Perfect for salads, cooking, and dipping.",
        "category": "groceries",
    },
    # --- Snacks ---
    {
        "id": "prod_almonds_500g",
        "name": "California Almonds 500g",
        "price": 35000,  # ₹350
        "stock": 30,
        "description": "Premium raw California almonds. Rich in vitamin E and healthy fats. Great for snacking or baking.",
        "category": "snacks",
    },
    {
        "id": "prod_dark_choc_200g",
        "name": "72% Dark Chocolate Bar 200g",
        "price": 22000,  # ₹220
        "stock": 50,
        "description": "Belgian dark chocolate, 72% cocoa. Smooth, rich flavor with subtle fruity notes.",
        "category": "snacks",
    },
    {
        "id": "prod_trail_mix_400g",
        "name": "Energy Trail Mix 400g",
        "price": 28000,  # ₹280
        "stock": 35,
        "description": "A blend of roasted cashews, almonds, dried cranberries, pumpkin seeds, and dark chocolate chips.",
        "category": "snacks",
    },
    # --- Personal Care ---
    {
        "id": "prod_shampoo_herbal",
        "name": "Herbal Anti-Dandruff Shampoo 300ml",
        "price": 32000,  # ₹320
        "stock": 20,
        "description": "Ayurvedic shampoo with neem, tea tree oil, and aloe vera. Gentle on scalp, tough on dandruff.",
        "category": "personal_care",
    },
    {
        "id": "prod_sunscreen_spf50",
        "name": "Matte Sunscreen SPF 50 100ml",
        "price": 49900,  # ₹499
        "stock": 18,
        "description": "Lightweight, non-greasy matte finish sunscreen. Broad-spectrum UVA/UVB protection. Water-resistant.",
        "category": "personal_care",
    },
    # --- Electronics ---
    {
        "id": "prod_usb_c_cable",
        "name": "Braided USB-C Cable 2m",
        "price": 59900,  # ₹599
        "stock": 60,
        "description": "Durable nylon-braided USB-C to USB-C cable. Supports 100W PD fast charging and 10Gbps data transfer.",
        "category": "electronics",
    },
    {
        "id": "prod_bt_earbuds",
        "name": "Wireless Bluetooth Earbuds",
        "price": 149900,  # ₹1,499
        "stock": 0,  # deliberately out of stock for failure demo
        "description": "Active noise cancelling wireless earbuds with 30-hour battery life. IPX5 water resistant.",
        "category": "electronics",
    },
]
