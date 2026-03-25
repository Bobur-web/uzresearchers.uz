"""
╔══════════════════════════════════════════════════════════╗
║         📀  DATABASE  —  SQLite ma'lumotlar bazasi      ║
║         Kitob Do'koni | Bot + Admin Panel               ║
╚══════════════════════════════════════════════════════════╝
"""

import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kitob_dunyosi.db")

_local = threading.local()


def get_conn():
    """Thread-safe ulanishni qaytaradi."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn.execute("PRAGMA busy_timeout=10000")
    return _local.conn


def init_db():
    """Jadvallarni yaratish."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            key       TEXT PRIMARY KEY,
            emoji     TEXT NOT NULL DEFAULT '📚',
            label     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS books (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT    NOT NULL,
            author        TEXT    NOT NULL,
            price_epub    INTEGER NOT NULL DEFAULT 0,
            price_book    INTEGER NOT NULL DEFAULT 0,
            cat           TEXT    NOT NULL DEFAULT '',
            description   TEXT    NOT NULL DEFAULT '',
            epub_url      TEXT    NOT NULL DEFAULT '',
            preview       TEXT    NOT NULL DEFAULT '',
            size_mb       TEXT    NOT NULL DEFAULT '1 MB',
            pages         INTEGER NOT NULL DEFAULT 0,
            year          INTEGER NOT NULL DEFAULT 2024,
            rating        REAL    NOT NULL DEFAULT 5.0,
            badge         TEXT    NOT NULL DEFAULT '',
            has_physical  INTEGER NOT NULL DEFAULT 0,
            stock         INTEGER NOT NULL DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cat) REFERENCES categories(key)
        );

        CREATE TABLE IF NOT EXISTS users (
            uid       INTEGER PRIMARY KEY,
            name      TEXT    NOT NULL DEFAULT '',
            username  TEXT    NOT NULL DEFAULT '',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id        TEXT PRIMARY KEY,
            uid             INTEGER NOT NULL,
            name            TEXT    NOT NULL DEFAULT '',
            total           INTEGER NOT NULL DEFAULT 0,
            address         TEXT,
            phone           TEXT,
            date            TEXT    NOT NULL,
            status          TEXT    NOT NULL DEFAULT '⏳ Kutmoqda',
            receipt_file_id TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uid) REFERENCES users(uid)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id  TEXT    NOT NULL,
            book_id   INTEGER NOT NULL,
            item_type TEXT    NOT NULL DEFAULT 'epub',
            qty       INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS wishlists (
            uid     INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            PRIMARY KEY (uid, book_id),
            FOREIGN KEY (uid) REFERENCES users(uid),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS purchased (
            uid     INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            PRIMARY KEY (uid, book_id),
            FOREIGN KEY (uid) REFERENCES users(uid),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
    """)
    conn.commit()


# ══════════════════════════════════════════════
#  KATEGORIYALAR
# ══════════════════════════════════════════════

def get_categories():
    """Barcha kategoriyalar dict: {key: (emoji, label)}"""
    rows = get_conn().execute("SELECT key, emoji, label FROM categories").fetchall()
    return {r["key"]: (r["emoji"], r["label"]) for r in rows}


def get_category(key):
    row = get_conn().execute("SELECT * FROM categories WHERE key=?", (key,)).fetchone()
    return dict(row) if row else None


def add_category(key, emoji, label):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO categories (key, emoji, label) VALUES (?,?,?)",
                 (key, emoji, label))
    conn.commit()


def update_category(old_key, new_key, emoji, label):
    conn = get_conn()
    if old_key != new_key:
        conn.execute("UPDATE books SET cat=? WHERE cat=?", (new_key, old_key))
        conn.execute("DELETE FROM categories WHERE key=?", (old_key,))
        conn.execute("INSERT INTO categories (key, emoji, label) VALUES (?,?,?)",
                     (new_key, emoji, label))
    else:
        conn.execute("UPDATE categories SET emoji=?, label=? WHERE key=?",
                     (emoji, label, old_key))
    conn.commit()


def delete_category(key):
    conn = get_conn()
    conn.execute("UPDATE books SET cat='' WHERE cat=?", (key,))
    conn.execute("DELETE FROM categories WHERE key=?", (key,))
    conn.commit()


# ══════════════════════════════════════════════
#  KITOBLAR
# ══════════════════════════════════════════════

def _book_to_dict(row):
    if not row:
        return None
    d = dict(row)
    d["has_physical"] = bool(d["has_physical"])
    d["desc"] = d.pop("description", "")
    return d


def get_books():
    """Barcha kitoblar dict: {id: {...}}"""
    rows = get_conn().execute("SELECT * FROM books ORDER BY id").fetchall()
    return {r["id"]: _book_to_dict(r) for r in rows}


def get_book(bid):
    row = get_conn().execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
    return _book_to_dict(row)


def get_books_by_filter(section=None, cat=None):
    """Filtrli kitoblar."""
    query = "SELECT * FROM books WHERE 1=1"
    params = []
    if section == "paid":
        query += " AND price_epub > 0"
    elif section == "free":
        query += " AND price_epub = 0"
    elif section == "physical":
        query += " AND has_physical = 1 AND stock > 0"
    if cat:
        query += " AND cat = ?"
        params.append(cat)
    rows = get_conn().execute(query, params).fetchall()
    return {r["id"]: _book_to_dict(r) for r in rows}


def add_book(title, author, price_epub=0, price_book=0, cat="", desc="",
             epub_url="", preview="", size_mb="1 MB", pages=0, year=2024,
             rating=5.0, badge="🆕 Yangi", has_physical=False, stock=0):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO books (title, author, price_epub, price_book, cat, description,
           epub_url, preview, size_mb, pages, year, rating, badge, has_physical, stock)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (title, author, price_epub, price_book, cat, desc,
         epub_url, preview, size_mb, pages, year, rating, badge,
         1 if has_physical else 0, stock))
    conn.commit()
    return cur.lastrowid


def update_book(bid, **kwargs):
    conn = get_conn()
    if "desc" in kwargs:
        kwargs["description"] = kwargs.pop("desc")
    if "has_physical" in kwargs:
        kwargs["has_physical"] = 1 if kwargs["has_physical"] else 0
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [bid]
    conn.execute(f"UPDATE books SET {sets} WHERE id=?", vals)
    conn.commit()


def delete_book(bid):
    conn = get_conn()
    conn.execute("DELETE FROM order_items WHERE book_id=?", (bid,))
    conn.execute("DELETE FROM wishlists WHERE book_id=?", (bid,))
    conn.execute("DELETE FROM purchased WHERE book_id=?", (bid,))
    conn.execute("DELETE FROM books WHERE id=?", (bid,))
    conn.commit()


def search_books(query):
    q = f"%{query}%"
    rows = get_conn().execute(
        "SELECT * FROM books WHERE title LIKE ? OR author LIKE ?", (q, q)).fetchall()
    return {r["id"]: _book_to_dict(r) for r in rows}


# ══════════════════════════════════════════════
#  FOYDALANUVCHILAR
# ══════════════════════════════════════════════

def get_users():
    rows = get_conn().execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
    return {r["uid"]: dict(r) for r in rows}


def get_user(uid):
    row = get_conn().execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
    return dict(row) if row else None


def upsert_user(uid, name, username=""):
    conn = get_conn()
    conn.execute(
        """INSERT INTO users (uid, name, username) VALUES (?,?,?)
           ON CONFLICT(uid) DO UPDATE SET name=excluded.name, username=excluded.username""",
        (uid, name, username))
    conn.commit()


def get_users_count():
    return get_conn().execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ══════════════════════════════════════════════
#  BUYURTMALAR
# ══════════════════════════════════════════════

def get_orders(status_filter=None):
    if status_filter:
        rows = get_conn().execute(
            "SELECT * FROM orders WHERE status LIKE ? ORDER BY created_at DESC",
            (f"%{status_filter}%",)).fetchall()
    else:
        rows = get_conn().execute(
            "SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_order(oid):
    row = get_conn().execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone()
    return dict(row) if row else None


def get_order_items(oid):
    """Buyurtma tarkibi: {book_id: {type, qty}}"""
    rows = get_conn().execute(
        "SELECT book_id, item_type, qty FROM order_items WHERE order_id=?",
        (oid,)).fetchall()
    return {r["book_id"]: {"type": r["item_type"], "qty": r["qty"]} for r in rows}


def create_order(oid, uid, name, items, total, address=None, phone=None, date_str=""):
    conn = get_conn()
    conn.execute(
        """INSERT INTO orders (order_id, uid, name, total, address, phone, date, status)
           VALUES (?,?,?,?,?,?,?,?)""",
        (oid, uid, name, total, address, phone, date_str, "⏳ Kutmoqda"))
    for bid, item in items.items():
        conn.execute(
            "INSERT INTO order_items (order_id, book_id, item_type, qty) VALUES (?,?,?,?)",
            (oid, bid, item["type"], item.get("qty", 1)))
    conn.commit()


def update_order_status(oid, status):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE order_id=?", (status, oid))
    conn.commit()


def update_order_receipt(oid, file_id):
    conn = get_conn()
    conn.execute("UPDATE orders SET receipt_file_id=? WHERE order_id=?", (file_id, oid))
    conn.commit()


def delete_order(oid):
    conn = get_conn()
    conn.execute("DELETE FROM order_items WHERE order_id=?", (oid,))
    conn.execute("DELETE FROM orders WHERE order_id=?", (oid,))
    conn.commit()


# ══════════════════════════════════════════════
#  ISTAKLAR
# ══════════════════════════════════════════════

def get_wishlist(uid):
    rows = get_conn().execute("SELECT book_id FROM wishlists WHERE uid=?", (uid,)).fetchall()
    return [r["book_id"] for r in rows]


def toggle_wishlist(uid, bid):
    conn = get_conn()
    existing = conn.execute(
        "SELECT 1 FROM wishlists WHERE uid=? AND book_id=?", (uid, bid)).fetchone()
    if existing:
        conn.execute("DELETE FROM wishlists WHERE uid=? AND book_id=?", (uid, bid))
        conn.commit()
        return False  # removed
    else:
        conn.execute("INSERT INTO wishlists (uid, book_id) VALUES (?,?)", (uid, bid))
        conn.commit()
        return True  # added


# ══════════════════════════════════════════════
#  XARIDLAR
# ══════════════════════════════════════════════

def get_purchased(uid):
    rows = get_conn().execute("SELECT book_id FROM purchased WHERE uid=?", (uid,)).fetchall()
    return [r["book_id"] for r in rows]


def add_purchased(uid, bid):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO purchased (uid, book_id) VALUES (?,?)", (uid, bid))
    conn.commit()


def get_purchased_count(uid):
    return get_conn().execute(
        "SELECT COUNT(*) FROM purchased WHERE uid=?", (uid,)).fetchone()[0]


# ══════════════════════════════════════════════
#  STATISTIKA
# ══════════════════════════════════════════════

def get_stats():
    conn = get_conn()
    books_count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM orders WHERE status LIKE '%⏳%'").fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM orders WHERE status LIKE '%✅%'").fetchone()[0]
    revenue = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM orders WHERE status LIKE '%✅%'").fetchone()[0]

    # Top kitoblar
    top_rows = conn.execute("""
        SELECT oi.book_id, b.title, SUM(oi.qty) as cnt
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN books b ON oi.book_id = b.id
        WHERE o.status LIKE '%✅%'
        GROUP BY oi.book_id
        ORDER BY cnt DESC
        LIMIT 5
    """).fetchall()
    top_books = [(r["book_id"], r["title"], r["cnt"]) for r in top_rows]

    return {
        "books_count": books_count,
        "users_count": users_count,
        "pending": pending,
        "confirmed": confirmed,
        "revenue": revenue,
        "top_books": top_books,
    }


# ══════════════════════════════════════════════
#  BOSHLANG'ICH MA'LUMOT
# ══════════════════════════════════════════════

def seed_defaults():
    """Bazada hech narsa yo'q bo'lsa, boshlang'ich ma'lumotlarni qo'shish."""
    conn = get_conn()
    cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if cat_count == 0:
        defaults = [
            ("roman", "📖", "Romanlar"),
            ("rivojlanish", "💡", "Shaxsiy rivojlanish"),
            ("fantastika", "🚀", "Fantastika"),
            ("bolalar", "🧸", "Bolalar uchun"),
            ("moliya", "💰", "Moliya & Biznes"),
        ]
        conn.executemany("INSERT INTO categories (key, emoji, label) VALUES (?,?,?)", defaults)
        conn.commit()

    book_count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    if book_count == 0:
        add_book(
            title="Alximist", author="Paulo Coelho",
            price_epub=25000, price_book=45000, cat="roman",
            desc="Santiago ismli yigitning orzusi ortidan borgan safari.",
            epub_url="https://drive.google.com/your-link",
            preview="https://drive.google.com/preview-link",
            size_mb="2.1 MB", pages=208, year=1988,
            rating=4.8, badge="🔥 Bestseller",
            has_physical=True, stock=10,
        )
        add_book(
            title="Bepul kitob namunasi", author="Muallif ismi",
            price_epub=0, price_book=0, cat="rivojlanish",
            desc="Bu bepul kitob tavsifi.",
            epub_url="https://drive.google.com/your-free-link",
            preview="", size_mb="1.5 MB", pages=150, year=2023,
            rating=4.5, badge="🎁 Bepul",
            has_physical=False, stock=0,
        )


if __name__ == "__main__":
    init_db()
    seed_defaults()
    print("✅ Ma'lumotlar bazasi tayyor!")
    print(f"📂 Fayl: {DB_PATH}")
    stats = get_stats()
    print(f"📚 Kitoblar: {stats['books_count']}")
    print(f"📂 Kategoriyalar: {len(get_categories())}")
