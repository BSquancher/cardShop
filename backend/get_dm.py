import requests
import psycopg2
from psycopg2.extras import Json
import os

mac_user = os.getlogin()
conn = psycopg2.connect(dbname="tcg_store", user=mac_user, host="localhost", port="5432")
cursor = conn.cursor()

query = """
    INSERT INTO cards (game_name, card_name, set_name, set_code, card_number, rarity, image_url, is_foil_only, tcgplayer_id, game_attributes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (game_name, card_name, set_name, card_number, rarity) DO NOTHING;
"""

print("🎯 Specifically targeting Dark Magician variants...")
try:
    # URL targeting fix
    res = requests.get("https://ygoprodeck.com").json()

    # FIX 1: Extract the card object out of the root 'data' list array wrapper
    card_data_list = res.get("data", [])
    if not card_data_list:
        print("❌ No data returned from the API.")
        exit()

    card = card_data_list[0] # Grab the actual card dictionary

    attrs = {
        "type": card.get("type"),
        "atk": card.get("atk"),
        "def": card.get("def"),
        "level": card.get("level"),
        "attribute": card.get("attribute")
    }

    # FIX 2: Handle images inside list bracket indexing safely
    images = card.get("card_images", [{}])
    default_img = images[0].get("image_url") if images else None
    card_sets = card.get("card_sets", [])

    for printing in card_sets:
        set_name = printing.get("set_name", "Unknown Set")
        set_code_full = printing.get("set_code", "N/A")
        set_code = set_code_full.split("-")[0] if "-" in set_code_full else "N/A"
        rarity = printing.get("set_rarity", "Common")

        cursor.execute(query, (
            "Yugioh", card.get("name"), set_name, set_code, set_code_full,
            rarity, default_img, False, None, Json(attrs)
        ))

    conn.commit()
    print(f"🎉 Success! Loaded {len(card_sets)} unique print variants of Dark Magician!")
except Exception as e:
    print(f"❌ Snagged an error: {e}")

cursor.close()
conn.close()
