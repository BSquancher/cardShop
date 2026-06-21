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

print("📥 Reading your local Pokémon data file ('Pokebase1.json')...")
try:
    with open("Pokebase1.json", "r") as f:
        pokemon_data = json.load(f)

    print(f"📦 Unpacking and saving {len(pokemon_data)} Pokémon cards into your database...")

    inserted_count = 0
    for card in pokemon_data:
        # Nesting game-specific characteristics cleanly inside your JSONB column
        attrs = {
            "hp": card.get("hp"),
            "types": card.get("types"),
            "subtypes": card.get("subtypes"),
            "attacks": card.get("attacks")
        }

        set_info = card.get("set", {})
        set_name = set_info.get("name", "Unknown Set")
        set_code = set_info.get("id", "N/A").upper()

        # Pull high-resolution card artwork link
        images = card.get("images", {})
        img_url = images.get("large") if images else None

        cursor.execute(query, (
            "Pokemon",              # game_name
            card.get("name"),       # card_name
            set_name,               # set_name
            set_code,               # set_code
            card.get("number"),     # card_number
            card.get("rarity"),     # rarity
            img_url,                # image_url
            False,                  # is_foil_only
            None,                   # tcgplayer_id (null for now)
            Json(attrs)             # game_attributes (JSONB)
        ))
        inserted_count += 1

    conn.commit()
    print(f"🎉 Success! Pokémon dataset populated. Total variants written: {inserted_count}")

except FileNotFoundError:
    print("❌ Pokémon sync failed: 'Pokebase1.json' was not found in this directory.")
    print("Make sure you place the file inside your active backend folder!")
except Exception as e:
    print(f"❌ Script processing error occurred: {e}")

cursor.close()
conn.close()
