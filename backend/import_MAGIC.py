import json
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

# The exact 10 columns matching your active schema layout
query = """
    INSERT INTO cards (game_name, card_name, set_name, set_code, card_number, rarity, image_url, is_foil_only, tcgplayer_id, game_attributes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (game_name, card_name, set_name, card_number, rarity) DO NOTHING;
"""

print("📥 Reading your local Magic data file ('MAGICList.json')...")
print("This file can be quite large, please give it a moment to load into memory...")

try:
    with open("MAGICList.json", "r") as f:
        mtg_data = json.load(f)

    print(f"📦 Unpacking and saving {len(mtg_data)} Magic cards into your database...")

    inserted_count = 0
    for card in mtg_data:
        # Filter down game-specific mechanics into the JSONB column
        attrs = {
            "mana_cost": card.get("mana_cost"),
            "cmc": card.get("cmc"),
            "type_line": card.get("type_line"),
            "oracle_text": card.get("oracle_text"),
            "colors": card.get("colors")
        }

        # Scryfall provides tcgplayer_id natively under 'tcgplayer_id'
        tcg_id = card.get("tcgplayer_id")

        # Isolate if a card only exists in a foil printing
        is_foil = card.get("foil", False) and not card.get("nonfoil", True)

        cursor.execute(query, (
            "Magic",                           # game_name
            card.get("name"),                  # card_name
            card.get("set_name"),              # set_name
            card.get("set", "").upper(),       # set_code
            card.get("collector_number"),      # card_number
            card.get("rarity"),                # rarity
            card.get("image_uris", {}).get("normal"), # image_url
            is_foil,                           # is_foil_only
            int(tcg_id) if tcg_id else None,   # tcgplayer_id
            Json(attrs)                        # game_attributes (JSONB)
        ))
        inserted_count += 1

        # Save progress in batches of 50,000 so your terminal memory stays clean
        if inserted_count % 50000 == 0:
            conn.commit()
            print(f"💾 Saved progress: {inserted_count} cards written to database...")

    conn.commit()
    print(f"🎉 Success! Magic dataset fully populated. Total variants saved: {inserted_count}")

except FileNotFoundError:
    print("❌ Magic sync failed: 'MAGICList.json' was not found in this directory.")
    print("Make sure you place the file inside your active backend folder!")
except Exception as e:
    print(f"❌ Script processing error occurred: {e}")

cursor.close()
conn.close()
