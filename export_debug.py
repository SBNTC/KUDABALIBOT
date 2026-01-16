import sqlite3

def export():
    conn = sqlite3.connect('events_buffer.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT chat_title, text, link, created_at FROM pending_messages ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    print(f"Найдено записей: {len(rows)}")
    
    with open("debug_report.txt", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(f"=== {r[0]} | {r[3]} ===\n")
            f.write(f"LINK: {r[2]}\n")
            f.write(f"TEXT:\n{r[1]}\n")
            f.write("-" * 50 + "\n\n")
            
    print("Сохранено в debug_report.txt")
    conn.close()

if __name__ == "__main__":
    export()
