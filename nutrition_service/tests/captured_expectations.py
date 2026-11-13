"""Expected values typed in by hand after capture_fixtures.py ran (spec 13.1).

Each value was read ONCE from the named fixture file and copied here. Tests
never compute an expected value from the fixture they are testing.

For 171999 and 172001 the values were fixed in the spec before capture.
"""

CHINOOK = {
    "file": "food_171999",
    "fdc_id": 171999,
    "description": "Fish, salmon, chinook, cooked, dry heat",
    "data_type": "SR Legacy",
    "saturated_fat_g": 3.214,
    "cholesterol_mg": 85.0,
}

PINK = {
    "file": "food_172001",
    "fdc_id": 172001,
    "description": "Fish, salmon, pink, cooked, dry heat",
    "data_type": "SR Legacy",
    "saturated_fat_g": 0.971,
    "cholesterol_mg": 55.0,
}

# Filled in after capture. Keys: file, fdc_id, description, data_type,
# saturated_fat_g, cholesterol_mg (None when USDA has no row), status.
# Spec 13.1 item 6: first Foundation result for "salmon". Read from food_foundation_2684441.json
# on 2026-11-01: rows nutrient.id 1258 amount 2.277 g, nutrient.id 1253 amount 62.11 mg.
FOUNDATION_ANIMAL: dict | None = {
    "file": "food_foundation_2684441",
    "fdc_id": 2684441,
    "description": "Fish, salmon, Atlantic, farm raised, raw",
    "data_type": "Foundation",
    "saturated_fat_g": 2.277,
    "cholesterol_mg": 62.11,
    "status": "complete",
}

# Spec 13.1 item 7: first Foundation result for "broccoli raw". Read from food_foundation_747447.json
# on 2026-11-01: one row only, nutrient.id 1258 amount 0.039 g; no cholesterol row at all.
FOUNDATION_PLANT: dict | None = {
    "file": "food_foundation_747447",
    "fdc_id": 747447,
    "description": "Broccoli, raw",
    "data_type": "Foundation",
    "saturated_fat_g": 0.039,
    "cholesterol_mg": None,
    "status": "partial",
}

# Spec 13.1 item 8: first Branded result for "salmon". Read from food_branded_2016166.json
# on 2026-11-01: dataType "Branded", so the service must refuse it regardless of its rows.
BRANDED: dict | None = {
    "file": "food_branded_2016166",
    "fdc_id": 2016166,
    "data_type": "Branded",
}

# Phase 2A recipe records, read once from the files named below on 2026-11-02 (capture_recipe_fixtures.py).
# fdc_id: (file, description, saturated_fat_g per 100 g, cholesterol_mg per 100 g)
RECIPE_RECORDS = {
    169249: ("food_169249", "Lettuce, green leaf, raw", 0.02, 0.0),
    170151: ("food_170151", "Seeds, sesame seeds, whole, roasted and toasted", 6.722, 0.0),
    170189: ("food_170189", "Seeds, sesame butter, tahini, from roasted and toasted kernels (most common type)", 7.529, 0.0),
    170457: ("food_170457", "Tomatoes, red, ripe, raw, year round average", 0.028, 0.0),
    171249: ("food_171249", "Cheese, romano", 17.115, 104.0),
    171413: ("food_171413", "Oil, olive, salad or cooking", 13.808, 0.0),
    172675: ("food_172675", "Bread, french or vienna (includes sourdough)", 0.529, 0.0),
    173706: ("food_173706", "Fish, tuna, fresh, bluefin, raw", 1.257, 38.0),
}
