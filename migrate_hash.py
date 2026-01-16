import sqlite3
import hashlib

def compute_hash(text):
    if not text:
        return None
    normalized = text.lower().strip()[:500]
    return hashlib.sha256(normalized.encode()).hexdigest()

conn = sqlite3.connect('events.db')
cursor = conn.cursor()

cursor.execute("SELECT id, raw_text FROM scraped_events WHERE text_hash IS NULL")
rows = cursor.fetchall()

print(f"Обновляю {len(rows)} записей...")

updated = 0
skipped = 0

for row_id, raw_text in rows:
    text_hash = compute_hash(raw_text)
    try:
        cursor.execute("UPDATE scraped_events SET text_hash = ? WHERE id = ?", (text_hash, row_id))
        updated += 1
    except sqlite3.IntegrityError:
        # Дубль - удаляем эту запись
        cursor.execute("DELETE FROM scraped_events WHERE id = ?", (row_id,))
        skipped += 1

conn.commit()
conn.close()
print(f"✅ Обновлено: {updated}, удалено дублей: {skipped}")
