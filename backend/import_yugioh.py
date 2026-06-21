import requests
import psycopg2
from psycopg2.extras import Json
import os

mac_user = os.getlogin()

print("🔌 Connecting to your local PostgreSQL database...")
conn = psycopg2.connect(
    dbname="tcg_store",
    user=mac_user,
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Wipe the database slate clean so we start completely fresh
cursor.execute("TRUNCATE TABLE cards;")

query = """
    INSERT INTO cards (game_name, card_name, set_name, set_code, card_number, rarity, image_url, is_foil_only, tcgplayer_id, game_attributes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (game_name, card_name, set_name, card_number, rarity) DO NOTHING;
"""

# Stripped down Accept-Encoding header so requests decompresses the stream automatically
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://ygoprodeck.com/'
}

print("📥 Fetching full Yu-Gi-Oh! catalog from the canonical data engine...")
try:
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Server connection refused! Status Code: {response.status_code}")
        cursor.close()
        conn.close()
        exit()

    try:
        # response.json() automatically decodes standard text bodies safely
        ygo_res = response.json()
    except Exception as parse_error:
        print("❌ Data payload parsing failed.")
        print(f"Details: {parse_error}")
        cursor.close()
        conn.close()
        exit()

    ygo_data = ygo_res.get("data", [])
    print(f"📦 Successfully connected! Processing and unpacking {len(ygo_data)} cards into variations...")

    inserted_count = 0
    for card in ygo_data:
        attrs = {
            "type": card.get("type"),
            "atk": card.get("atk"),
            "def": card.get("def"),
            "level": card.get("level"),
            "attribute": card.get("attribute")
        }

        # Safely extract image arrays
        images = card.get("card_images", [])
        default_img = images[0].get("image_url") if isinstance(images, list) and len(images) > 0 else None

        card_sets = card.get("card_sets", [])

        if not card_sets:
            cursor.execute(query, ("Yugioh", card.get("name"), "Promo", "N/A", "N/A", "Common", default_img, False, None, Json(attrs)))
            inserted_count += 1
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
            inserted_count += 1

    conn.commit()
    print(f"🎉 Success! Local Yu-Gi-Oh dataset populated. Total items written: {inserted_count}")

except Exception as e:
    print(f"❌ Script processing error occurred: {e}")

cursor.close()
conn.close()
