"""Demo data used by local runs and tests."""

ADMIN_KEY = "sk_admin_ops"

SEED = {
    "customers": [
        {"id": "cus_alice", "name": "Alice", "api_key": "sk_alice"},
        {"id": "cus_bob", "name": "Bob", "api_key": "sk_bob"},
    ],
    "restaurants": [
        {"id": "res_dragon", "name": "Dragon Noodle House", "timezone": "America/Toronto", "utc_offset_minutes": -240,
         "opens_at": "11:00", "closes_at": "22:00", "commission_bps": 2000},
        {"id": "res_slice", "name": "Late Slice", "timezone": "America/Vancouver", "utc_offset_minutes": -420,
         "opens_at": "18:00", "closes_at": "02:00", "commission_bps": 1800},
    ],
    "menu_items": [
        {"id": "itm_dumplings", "restaurant_id": "res_dragon", "name": "Pork dumplings", "price": 1095},
        {"id": "itm_bao", "restaurant_id": "res_dragon", "name": "Bao (2)", "price": 335},
        {"id": "itm_rolls", "restaurant_id": "res_dragon", "name": "Spring rolls", "price": 335},
        {"id": "itm_soup", "restaurant_id": "res_dragon", "name": "Hot and sour soup", "price": 335},
        {"id": "itm_noodles", "restaurant_id": "res_dragon", "name": "Dan dan noodles", "price": 1450},
        {"id": "itm_pep", "restaurant_id": "res_slice", "name": "Pepperoni slice", "price": 450},
        {"id": "itm_garlic", "restaurant_id": "res_slice", "name": "Garlic knots", "price": 599},
    ],
    "promos": [
        {"code": "SAVE10", "percent_off": 10, "active": 1},
        {"code": "WELCOME15", "percent_off": 15, "active": 1},
    ],
    "couriers": [
        {"id": "cou_maya", "name": "Maya", "on_shift": 1, "active_jobs": 0},
        {"id": "cou_raj", "name": "Raj", "on_shift": 1, "active_jobs": 0},
    ],
}
