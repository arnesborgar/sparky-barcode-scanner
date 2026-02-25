#!/usr/bin/env python3
"""
Raspberry Pi Barcode Scanner → SparkyFitness Food Logger

Reads barcodes from a USB barcode scanner (keyboard HID device),
looks up nutrition via OpenFoodFacts through SparkyFitness API,
creates the food if needed, and logs it to the food diary.

Usage:
    sudo python3 barcode_scanner.py

Configuration:
    Copy .env.example to .env and fill in your values, or set env vars:
      SPARKY_URL        - SparkyFitness base URL (e.g. http://10.1.1.86)
      SPARKY_API_KEY    - API key with diary permission
      SCANNER_DEVICE    - evdev input device path (auto-detected if omitted)
"""

import os
import re
import sys
import json
import signal
import logging
from datetime import date
from pathlib import Path

import requests
import evdev

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_dotenv(path: Path):
    """Minimal .env loader — no external dependency needed."""
    if not path.is_file():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key:
                os.environ.setdefault(key, value)


load_dotenv(Path(__file__).parent / ".env")

SPARKY_URL = os.environ.get("SPARKY_URL", "http://localhost:3010").rstrip("/")
SPARKY_API_KEY = os.environ.get("SPARKY_API_KEY", "")
SCANNER_DEVICE = os.environ.get("SCANNER_DEVICE", "")
USDA_PROVIDER_ID = os.environ.get("USDA_PROVIDER_ID", "")

# Time windows for auto meal type (24h format, configurable via env)
# Format: HH:MM-HH:MM  — scans outside all windows default to Snack
MEAL_WINDOWS = {
    "Breakfast": os.environ.get("BREAKFAST_WINDOW", "05:00-10:00"),
    "Lunch":     os.environ.get("LUNCH_WINDOW",     "11:00-13:00"),
    "Dinner":    os.environ.get("DINNER_WINDOW",    "14:00-16:00"),
}

if not SPARKY_API_KEY:
    sys.exit("ERROR: SPARKY_API_KEY is not set. Export it or add to .env")

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": SPARKY_API_KEY,
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Timeouts: (connect, read) in seconds
TIMEOUT = (5, 15)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scanner")


def current_meal_type() -> str:
    """Determine meal type based on current time of day."""
    from datetime import datetime
    now = datetime.now().time()
    for meal, window in MEAL_WINDOWS.items():
        start_str, end_str = window.split("-")
        start = datetime.strptime(start_str.strip(), "%H:%M").time()
        end = datetime.strptime(end_str.strip(), "%H:%M").time()
        if start <= now < end:
            return meal
    return "Snack"

# ---------------------------------------------------------------------------
# OpenFoodFacts → SparkyFitness nutrient mapping (per 100g keys)
# ---------------------------------------------------------------------------

NUTRIENT_MAP = {
    "energy-kcal_100g":          "calories",
    "proteins_100g":             "protein",
    "carbohydrates_100g":        "carbs",
    "fat_100g":                  "fat",
    "saturated-fat_100g":        "saturated_fat",
    "polyunsaturated-fat_100g":  "polyunsaturated_fat",
    "monounsaturated-fat_100g":  "monounsaturated_fat",
    "trans-fat_100g":            "trans_fat",
    "cholesterol_100g":          "cholesterol",
    "sodium_100g":               "sodium",
    "potassium_100g":            "potassium",
    "fiber_100g":                "dietary_fiber",
    "sugars_100g":               "sugars",
    "vitamin-a_100g":            "vitamin_a",
    "vitamin-c_100g":            "vitamin_c",
    "calcium_100g":              "calcium",
    "iron_100g":                 "iron",
}

# USDA FoodData Central nutrient IDs → SparkyFitness field names
USDA_NUTRIENT_MAP = {
    1008: "calories",
    1003: "protein",
    1005: "carbs",
    1004: "fat",
    1258: "saturated_fat",
    1293: "polyunsaturated_fat",
    1292: "monounsaturated_fat",
    1257: "trans_fat",
    1253: "cholesterol",
    1093: "sodium",
    1092: "potassium",
    1079: "dietary_fiber",
    2000: "sugars",
    1106: "vitamin_a",
    1162: "vitamin_c",
    1087: "calcium",
    1089: "iron",
}

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def lookup_barcode(barcode: str) -> dict | None:
    """Step 1 — Look up barcode via SparkyFitness → OpenFoodFacts proxy."""
    url = f"{SPARKY_URL}/api/foods/openfoodfacts/barcode/{barcode}"
    resp = SESSION.get(url, timeout=TIMEOUT)
    if resp.status_code != 200:
        log.warning("Barcode lookup failed (%d): %s", resp.status_code, resp.text[:200])
        return None
    data = resp.json()
    if data.get("status") != 1 or "product" not in data:
        log.warning("Product not found in OpenFoodFacts for barcode %s", barcode)
        return None
    return data["product"]


def build_food_suggestion(product: dict) -> dict:
    """Map an OFF product to a SparkyFitness food object.

    Food is stored with serving_size=100g so logging N grams = quantity N/100.
    This makes scale-based weight logging straightforward.
    """
    nutriments = product.get("nutriments", {})

    raw_name = product.get("product_name") or "Unknown Product"
    raw_brand = product.get("brands") or ""

    suggestion = {
        "name": raw_name.title() if raw_name.isupper() else raw_name,
        "brand": raw_brand.title() if raw_brand.isupper() else raw_brand,
        "barcode": product.get("code") or "",
        "provider_type": "openfoodfacts",
        "provider_external_id": None,
        "shared_with_public": False,
        "glycemic_index": None,
        "custom_nutrients": {},
        "serving_size": 100,
        "serving_unit": "g",
        "is_custom": True,
    }

    # Nutrients from OFF are already per 100g — store as-is
    for off_key, sparky_key in NUTRIENT_MAP.items():
        val = nutriments.get(off_key)
        suggestion[sparky_key] = round(float(val), 2) if val is not None else 0

    # Fill gaps from estimated nutriments (computed from ingredients)
    estimated = product.get("nutriments_estimated", {})
    if estimated:
        for off_key, sparky_key in NUTRIENT_MAP.items():
            if suggestion.get(sparky_key, 0) == 0:
                val = estimated.get(off_key)
                if val is not None and float(val) > 0:
                    suggestion[sparky_key] = round(float(val), 2)

    return suggestion


def is_nutrition_complete(suggestion: dict) -> bool:
    """Check if core macros are present (not all zero)."""
    return any(suggestion.get(k, 0) > 0 for k in ("protein", "carbs", "fat"))


def lookup_usda(query: str) -> dict | None:
    """Search USDA via SparkyFitness's built-in provider."""
    if not USDA_PROVIDER_ID:
        return None
    url = f"{SPARKY_URL}/api/food-integration/usda/search"
    resp = SESSION.get(
        url,
        params={"query": query},
        headers={"x-provider-id": USDA_PROVIDER_ID},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        log.warning("USDA search failed (%d)", resp.status_code)
        return None
    foods = resp.json().get("foods", [])
    return foods[0] if foods else None


def enrich_from_usda(suggestion: dict, usda_food: dict):
    """Fill in missing nutrients from USDA data (only zero-valued fields)."""
    for nutrient in usda_food.get("foodNutrients", []):
        nutrient_id = nutrient.get("nutrientId")
        sparky_key = USDA_NUTRIENT_MAP.get(nutrient_id)
        if sparky_key and suggestion.get(sparky_key, 0) == 0:
            val = nutrient.get("value")
            if val is not None and float(val) > 0:
                suggestion[sparky_key] = round(float(val), 2)


def create_or_get_food(suggestion: dict) -> tuple[str, str] | tuple[None, None]:
    """Step 2 — Create food via direct endpoint, return (foodId, variantId)."""
    url = f"{SPARKY_URL}/api/foods"
    resp = SESSION.post(url, json=suggestion, timeout=TIMEOUT)
    if resp.status_code not in (200, 201):
        log.error("food create failed (%d): %s", resp.status_code, resp.text[:200])
        return None, None
    data = resp.json()
    variant = data.get("default_variant", {})
    return data.get("id"), variant.get("id")


def log_food_entry(
    food_id: str,
    variant_id: str,
    meal_type: str,
    weight_grams: float | None = None,
) -> bool:
    """Step 3 — Create a food diary entry for today.

    If weight_grams is provided (from scale), log that exact weight.
    Since food is stored per 100g, quantity = weight / 100.
    Without a scale, logs 1 serving (= 100g).
    """
    url = f"{SPARKY_URL}/api/food-entries"
    if weight_grams is not None:
        quantity = round(weight_grams / 100, 2)
    else:
        quantity = 1
    body = {
        "food_id": food_id,
        "variant_id": variant_id,
        "meal_type": meal_type,
        "quantity": quantity,
        "unit": "serving",
        "entry_date": date.today().isoformat(),
    }
    resp = SESSION.post(url, json=body, timeout=TIMEOUT)
    if resp.status_code not in (200, 201):
        log.error("food-entry creation failed (%d): %s", resp.status_code, resp.text[:200])
        return False
    return True

# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def get_scale_weight() -> float | None:
    """Read weight from ESPHome scale.

    Returns grams if a scale is configured, None otherwise.
    """
    scale_url = os.environ.get("SCALE_URL")  # e.g. http://10.1.1.x/sensor/weight
    if not scale_url:
        return None
    try:
        resp = requests.get(scale_url, timeout=(2, 5))
        if resp.status_code == 200:
            data = resp.json()
            weight = float(data.get("value", 0))
            if weight > 0:
                return weight
            log.warning("Scale reads 0g — logging as 100g default")
    except Exception as e:
        log.warning("Scale read failed (%s) — logging as 100g default", e)
    return None


def process_barcode(barcode: str, meal_type: str | None = None):
    """Run the full scan → lookup → create → log pipeline."""
    if meal_type is None:
        meal_type = current_meal_type()
    log.info("━━━ Scanned: %s ━━━", barcode)

    # 1. Lookup
    product = lookup_barcode(barcode)
    if not product:
        return
    name = product.get("product_name", "?")
    brand = product.get("brands", "")
    log.info("Found: %s (%s)", name, brand)

    # 2. Build food data from OFF
    suggestion = build_food_suggestion(product)

    # 3. Enrich from USDA if macros are incomplete
    if not is_nutrition_complete(suggestion):
        log.info("  OFF data incomplete — trying USDA…")
        usda_food = (
            lookup_usda(barcode)
            or lookup_usda(f"{brand} {name}" if brand else name)
            or lookup_usda(name)
        )
        if usda_food:
            enrich_from_usda(suggestion, usda_food)
            log.info("  Enriched from USDA")
        else:
            log.warning("  USDA also has no data")

    # Flag for manual review if still incomplete
    if not is_nutrition_complete(suggestion):
        suggestion["name"] += " [REVIEW]"
        suggestion.setdefault("custom_nutrients", {})["needs_review"] = True
        log.warning("  ⚠ Nutrition incomplete — flagged for review")

    log.info(
        "  Per 100g — %.0f kcal | P:%.1fg C:%.1fg F:%.1fg",
        suggestion["calories"],
        suggestion["protein"],
        suggestion["carbs"],
        suggestion["fat"],
    )

    # 4. Create food & get IDs
    food_id, variant_id = create_or_get_food(suggestion)
    if not food_id or not variant_id:
        return

    # 5. Read scale (if available) & log entry
    weight = get_scale_weight()
    if log_food_entry(food_id, variant_id, meal_type, weight):
        if weight:
            kcal = suggestion["calories"] * weight / 100
            log.info("  ✓ Logged %.0fg (%.0f kcal) as %s", weight, kcal, meal_type)
        else:
            log.info("  ✓ Logged 100g (%.0f kcal) as %s", suggestion["calories"], meal_type)
    else:
        log.error("  ✗ Failed to log entry")

# ---------------------------------------------------------------------------
# USB barcode scanner input (evdev / keyboard HID)
# ---------------------------------------------------------------------------

def find_scanner_device() -> str:
    """Auto-detect a USB barcode scanner from /dev/input/ devices."""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for dev in devices:
        name_lower = (dev.name or "").lower()
        # Common barcode scanner identifiers
        if any(kw in name_lower for kw in ("barcode", "scanner", "hid")):
            log.info("Auto-detected scanner: %s (%s)", dev.name, dev.path)
            return dev.path
    # Fallback: list available and let user decide
    log.warning("Could not auto-detect scanner. Available input devices:")
    for dev in devices:
        log.warning("  %s — %s", dev.path, dev.name)
    sys.exit("Set SCANNER_DEVICE in .env to the correct /dev/input/eventN path")


# evdev key-code → character mapping for digits (barcode scanners send KEY_* events)
KEY_MAP = {
    evdev.ecodes.KEY_0: "0", evdev.ecodes.KEY_1: "1", evdev.ecodes.KEY_2: "2",
    evdev.ecodes.KEY_3: "3", evdev.ecodes.KEY_4: "4", evdev.ecodes.KEY_5: "5",
    evdev.ecodes.KEY_6: "6", evdev.ecodes.KEY_7: "7", evdev.ecodes.KEY_8: "8",
    evdev.ecodes.KEY_9: "9",
}


def read_barcodes_evdev(device_path: str):
    """
    Read barcodes from a USB HID scanner via evdev.
    Scanners send digit key-down events followed by KEY_ENTER.
    """
    dev = evdev.InputDevice(device_path)
    dev.grab()  # Exclusive access — prevent keystrokes going to console
    log.info("Listening on %s (%s) …", dev.path, dev.name)
    log.info("Meal type: auto (by time of day)  |  Ctrl+C to quit")

    buffer = []
    try:
        for event in dev.read_loop():
            if event.type != evdev.ecodes.EV_KEY:
                continue
            key_event = evdev.categorize(event)
            if key_event.keystate != evdev.KeyEvent.key_down:
                continue

            if key_event.scancode == evdev.ecodes.KEY_ENTER:
                barcode = "".join(buffer)
                buffer.clear()
                if barcode:
                    process_barcode(barcode)
            elif key_event.scancode in KEY_MAP:
                buffer.append(KEY_MAP[key_event.scancode])
    finally:
        dev.ungrab()


def read_barcodes_stdin():
    """Fallback: read barcodes from stdin (for testing without a scanner)."""
    log.info("No scanner device — reading barcodes from stdin (type barcode + Enter)")
    log.info("Meal type: auto (by time of day)  |  Ctrl+C to quit")
    try:
        while True:
            line = input("barcode> ").strip()
            if line:
                process_barcode(line)
    except EOFError:
        pass

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    log.info("SparkyFitness Barcode Scanner")
    log.info("Server: %s", SPARKY_URL)

    # Decide input mode
    device_path = SCANNER_DEVICE
    if not device_path:
        # Try auto-detect, fall back to stdin if no evdev devices
        try:
            device_path = find_scanner_device()
        except (FileNotFoundError, PermissionError, SystemExit):
            read_barcodes_stdin()
            return

    read_barcodes_evdev(device_path)


if __name__ == "__main__":
    main()
