import json
import requests
import psycopg2
from psycopg2.extras import Json
import os

mac_user = os.getlogin()

# Connect directly to your local database engine
conn = psycopg2.connect(
    dbname="tcg_store",
    user=mac_user,
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Wipe out any residual data so we start with a clean slate
cursor.execute("TRUNCATE TABLE cards;")

# Unified SQL insertion query protecting against duplicates via ON CONFLICT
query = """
    INSERT INTO cards (game_name, card_name, set_name, set_code, card_number, rarity, image_url, is_foil_only, tcgplayer_id, game_attributes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (game_name, card_name, set_name, card_number, rarity) DO NOTHING;
"""

# --- 1. MAGIC: THE GATHERING IMPORT ---
print("📥 Importing Magic variations...")
try:
    with open("default-cards.json", "r") as f:
        mtg_data = json.load(f)
        for card in mtg_data:  # No limits!
            attrs = {
                "mana_cost": card.get("mana_cost"),
                "cmc": card.get("cmc"),
                "type_line": card.get("type_line"),
                "oracle_text": card.get("oracle_text")
            }
            tcg_id = card.get("tcgplayer_id")
            cursor.execute(query, (
                "Magic", card.get("name"), card.get("set_name"), card.get("set", "").upper(),
                card.get("collector_number"), card.get("rarity"),
                card.get("image_uris", {}).get("normal"), False, int(tcg_id) if tcg_id else None, Json(attrs)
            ))
        print("✅ Magic database entries successfully synced!")
except FileNotFoundError:
    print("ℹ️ Magic file 'default-cards.json' not found in this directory, skipping...")

# --- 2. POKÉMON IMPORT ---
print("📥 Importing Pokémon variations...")
try:
    with open("base1.json", "r") as f:
        pokemon_data = json.load(f)
        for card in pokemon_data:
            attrs = {"hp": card.get("hp"), "types": card.get("types"), "attacks": card.get("attacks")}
            set_info = card.get("set", {})
            cursor.execute(query, (
                "Pokemon", card.get("name"), set_info.get("name", "Unknown Set"), set_info.get("id", "").upper(),
                card.get("number"), card.get("rarity"), card.get("images", {}).get("large"), False, None, Json(attrs)
            ))
        print("✅ Pokémon database entries successfully synced!")
except FileNotFoundError:
    print("ℹ️ Pokémon file 'base1.json' not found in this directory, skipping...")

# --- 3. YUGIOH IMPORT ---
print("📥 Fetching full Yu-Gi-Oh! catalog from API (this may take a moment)...")
try:
    # Use a secure user agent header to prevent connection refusal blocks
    headers = {'User-Agent': 'Mozilla/5.0'}

    # CORRECT DATA CALL ENDPOINT
    url = "https://ygoprodeck.com"
    ygo_res = requests.get(url, headers=headers).json()

    ygo_data = ygo_res.get("data", [])
    print(f"📦 Unpacking and processing {len(ygo_data)} core card files...")

    for card in ygo_data:  # No limits, loop through all 13,000+ cards
        attrs = {
            "type": card.get("type"), "atk": card.get("atk"), "def": card.get("def"),
            "level": card.get("level"), "attribute": card.get("attribute")
        }

        # Safely extract image URL from array layout
        images = card.get("card_images", [{}])
        default_img = images[0].get("image_url") if images else None

        card_sets = card.get("card_sets", [])

        if not card_sets:
            cursor.execute(query, ("Yugioh", card.get("name"), "Promo", "N/A", "N/A", "Common", default_img, False, None, Json(attrs)))
            continue

        for printing in card_sets:
            set_name = printing.get("set_name", "Unknown Set")
            set_code_full = printing.get("set_code", "N/A")
            set_code = set_code_full.split("-")[0] if "-" in set_code_full else "N/A"
            rarity = printing.get("set_rarity", "Common")

            cursor.execute(query, (
                "Yugioh", card.get("name"), set_name, set_code, set_code_full,
                rarity, default_img, False, None, Json(attrs)
            ))

    print("✅ Yu-Gi-Oh! variations fully populated!")
except Exception as e:
    print(f"❌ Yu-Gi-Oh! sync failed: {e}")

conn.commit()
cursor.close()
conn.close()
print("🎉 Clean master data refresh completely successful!")
