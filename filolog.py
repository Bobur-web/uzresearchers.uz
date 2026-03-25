"""
╔══════════════════════════════════════════════════════════╗
║         📱  KITOB DUNYOSI  —  E-Book Do'koni            ║
║         Telegram Bot | PDF | Admin tasdiqlash           ║
╚══════════════════════════════════════════════════════════╝

O'rnatish:
    pip install -r requirements.txt

Ishga tushirish:
    python filolog.py
"""

import os
import telebot
from telebot import types
from datetime import datetime
import random

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import database as db

# ══════════════════════════════════════════════
#  SOZLAMALAR
# ══════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "8636504441:AAH9qKZgPjn88qy1t0mWjrNhn-UAKTnj0BM")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "1008681848"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Bazani ishga tushirish
db.init_db()
db.seed_defaults()

PDF_APPS = (
    "📱 *PDF o'qish uchun ilovalar:*\n"
    "🍎 iPhone/iPad: Apple Books, Adobe Acrobat\n"
    "🤖 Android: Adobe Acrobat, ReadEra\n"
    "💻 Windows/Mac: Adobe Reader, Foxit\n"
    "🌐 Brauzer: Chrome, Edge"
)

QUOTES = [
    '"Kitob — fikrning ko\'zgusi." — Francis Bacon',
    '"O\'qish — bu kelajakka investitsiya." — Benjamin Franklin',
    '"Bir kitob ming do\'stga teng." — A.P. Chexov',
    '"Kitob o\'qigan odam hech qachon yolg\'iz emas." — Hemingway',
]

# ══════════════════════════════════════════════
#  XOTIRA (faqat vaqtincha: cart va state)
# ══════════════════════════════════════════════
carts  = {}
states = {}

# ══════════════════════════════════════════════
#  YORDAMCHI
# ══════════════════════════════════════════════
def fmt(n):
    return f"{n:,}".replace(",", " ") + " so'm"

def stars(r):
    return "★" * int(r) + "☆" * (5 - int(r)) + f" {r}"

def new_order_id():
    return f"EB-{datetime.now().strftime('%d%m%H%M%S')}"

def is_admin(uid):
    return uid == ADMIN_ID

def get_price(bid, order_type):
    b = db.get_book(bid)
    return (b["price_epub"] if order_type == "epub" else b["price_book"]) if b else 0

def cart_total(uid):
    return sum(get_price(bid, i["type"]) * i.get("qty", 1) for bid, i in carts.get(uid, {}).items())

# ══════════════════════════════════════════════
#  KLAVIATURALAR
# ══════════════════════════════════════════════
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("📚 Kutubxona", "🛒 Savatcha", "🔍 Qidirish",
           "❤️ Istaklar", "📥 Kitoblarim", "💬 Yordam")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("⏳ Kutayotgan buyurtmalar", "✅ Tasdiqlangan buyurtmalar",
           "👥 Foydalanuvchilar", "📊 Statistika",
           "📖 Kitoblar bazasi", "📢 Xabar yuborish",
           "🔙 Asosiy menyu")
    return kb

def admin_books_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("➕ Yangi kitob", "✏️ Tahrirlash", "🗑 O'chirish", "🔙 Admin Panel")
    return kb

# ══════════════════════════════════════════════
#  /START
# ══════════════════════════════════════════════
@bot.message_handler(commands=["start"])
def cmd_start(m):
    uid = m.chat.id
    db.upsert_user(uid, m.from_user.first_name, m.from_user.username or "")
    books_count = db.get_stats()["books_count"]
    bot.send_message(uid,
        f"╔═══════════════════════╗\n║  📱  KITOB DUNYOSI   ║\n║     E-Book Do'koni    ║\n╚═══════════════════════╝\n\n"
        f"Salom, *{m.from_user.first_name}*! 👋\n\n_{random.choice(QUOTES)}_\n\n"
        f"📚 *{books_count} ta kitob* sizni kutmoqda.\nMenyudan foydalaning 👇",
        reply_markup=main_kb())

# ══════════════════════════════════════════════
#  KUTUBXONA — 1-QADAM
# ══════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📚 Kutubxona")
def show_library(m):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💎 Pullik e-kitoblar", callback_data="section_paid"),
        types.InlineKeyboardButton("🎁 Bepul e-kitoblar",  callback_data="section_free"),
        types.InlineKeyboardButton("📦 Qog'oz kitoblar",   callback_data="section_physical"),
    )
    bot.send_message(m.chat.id, "📚 *Kutubxona*\n\nQaysi bo'limni ko'rmoqchisiz?", reply_markup=kb)

# ══════════════════════════════════════════════
#  2-QADAM: KATEGORIYALAR
# ══════════════════════════════════════════════
def show_cats(chat_id, msg_id, section):
    filtered = db.get_books_by_filter(section=section)
    categories = db.get_categories()

    if section == "paid":
        title = "💎 *Pullik e-kitoblar*"
    elif section == "free":
        title = "🎁 *Bepul e-kitoblar*"
    else:
        title = "📦 *Qog'oz kitoblar*"

    cat_counts = {}
    for b in filtered.values():
        c = b.get("cat", "")
        if c:
            cat_counts[c] = cat_counts.get(c, 0) + 1

    kb = types.InlineKeyboardMarkup(row_width=1)
    for key, (emoji, label) in categories.items():
        if key in cat_counts:
            kb.add(types.InlineKeyboardButton(
                f"{emoji} {label} ({cat_counts[key]} ta)", callback_data=f"cat_{section}_{key}"))
    if not cat_counts:
        kb.add(types.InlineKeyboardButton("📭 Hozircha kitob yo'q", callback_data="noop"))
    kb.add(types.InlineKeyboardButton("◀ Orqaga", callback_data="back_sections"))
    bot.edit_message_text(f"{title}\n\nKategoriyani tanlang:", chat_id, msg_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("section_"))
def cb_section(c):
    show_cats(c.message.chat.id, c.message.message_id, c.data[8:])

@bot.callback_query_handler(func=lambda c: c.data == "back_sections")
def cb_back_sections(c):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💎 Pullik e-kitoblar", callback_data="section_paid"),
        types.InlineKeyboardButton("🎁 Bepul e-kitoblar",  callback_data="section_free"),
        types.InlineKeyboardButton("📦 Qog'oz kitoblar",   callback_data="section_physical"),
    )
    bot.edit_message_text("📚 *Kutubxona*\n\nQaysi bo'limni ko'rmoqchisiz?",
                          c.message.chat.id, c.message.message_id, reply_markup=kb)

# ══════════════════════════════════════════════
#  3-QADAM: KITOBLAR
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def cb_cat(c):
    _, section, cat_key = c.data.split("_", 2)
    uid   = c.from_user.id
    owned = db.get_purchased(uid)
    books = db.get_books_by_filter(section=section, cat=cat_key)
    categories = db.get_categories()

    emoji, label = categories.get(cat_key, ("📚", cat_key))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for bid, b in books.items():
        if section == "free":
            txt = f"🎁 {b['title']} — Bepul"
        elif bid in owned:
            txt = f"✅ {b['title']}"
        elif section == "paid":
            txt = f"📱 {b['title']} — {fmt(b['price_epub'])}"
        else:
            txt = f"📦 {b['title']} — {fmt(b['price_book'])}"
        kb.add(types.InlineKeyboardButton(txt, callback_data=f"book_{section}_{bid}"))
    if not books:
        kb.add(types.InlineKeyboardButton("📭 Bu kategoriyada kitob yo'q", callback_data="noop"))
    kb.add(types.InlineKeyboardButton("◀ Orqaga", callback_data=f"section_{section}"))
    bot.edit_message_text(f"{emoji} *{label}*\n\nKitobni tanlang:",
                          c.message.chat.id, c.message.message_id, reply_markup=kb)

# ══════════════════════════════════════════════
#  4-QADAM: KITOB TAFSILOTI
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("book_"))
def cb_book(c):
    _, section, bid_str = c.data.split("_", 2)
    bid = int(bid_str)
    uid = c.from_user.id
    b   = db.get_book(bid)
    if not b:
        bot.answer_callback_query(c.id, "Kitob topilmadi!"); return

    owned   = bid in db.get_purchased(uid)
    in_wish = bid in db.get_wishlist(uid)
    cat_key = b.get("cat", "")

    if section == "free":
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id,
            f"📥 *{b['title']}* — Bepul e-kitob\n✍️ {b['author']}\n\n"
            f"🔗 [PDF yuklab olish]({b['epub_url']})\n💾 Hajm: {b['size_mb']}\n\n{PDF_APPS}",
            disable_web_page_preview=True)
        return

    if section == "paid":
        txt = (f"📚 *{b['title']}*  {b.get('badge','')}\n{'─'*24}\n"
               f"✍️ *{b['author']}*\n📅 {b['year']}  |  📄 {b['pages']} sahifa\n"
               f"⭐ {stars(b['rating'])}\n\n📱 *E-kitob:* {fmt(b['price_epub'])}\n"
               f"💾 {b['size_mb']}\n\n📝 _{b['desc']}_")
        kb = types.InlineKeyboardMarkup(row_width=1)
        if owned:
            kb.add(types.InlineKeyboardButton("📥 Yuklab olish", callback_data=f"download_{bid}"))
        else:
            kb.add(types.InlineKeyboardButton(f"📱 Savatchaga qo'sh — {fmt(b['price_epub'])}", callback_data=f"add_epub_{bid}"))
        kb.add(types.InlineKeyboardButton("💔 Istakdan chiqar" if in_wish else "❤️ Istakka qo'sh", callback_data=f"wish_{bid}"))
        if b.get("preview"):
            kb.add(types.InlineKeyboardButton("👁 Namuna ko'rish", callback_data=f"preview_{bid}"))
        kb.add(types.InlineKeyboardButton("◀ Orqaga", callback_data=f"cat_paid_{cat_key}"))
        bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, reply_markup=kb)
        return

    if section == "physical":
        txt = (f"📦 *{b['title']}*  {b.get('badge','')}\n{'─'*24}\n"
               f"✍️ *{b['author']}*\n📅 {b['year']}  |  📄 {b['pages']} sahifa\n"
               f"⭐ {stars(b['rating'])}\n\n📦 *Qog'oz kitob:* {fmt(b['price_book'])}\n"
               f"🏪 Omborda: {b['stock']} ta\n\n📝 _{b['desc']}_")
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton(f"📦 Savatchaga qo'sh — {fmt(b['price_book'])}", callback_data=f"add_book_{bid}"))
        kb.add(types.InlineKeyboardButton("💔 Istakdan chiqar" if in_wish else "❤️ Istakka qo'sh", callback_data=f"wish_{bid}"))
        kb.add(types.InlineKeyboardButton("◀ Orqaga", callback_data=f"cat_physical_{cat_key}"))
        bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, reply_markup=kb)

# ══════════════════════════════════════════════
#  SAVATGA QO'SHISH
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("add_epub_"))
def cb_add_epub(c):
    uid = c.from_user.id; bid = int(c.data[9:])
    b = db.get_book(bid)
    carts.setdefault(uid, {})[bid] = {"type": "epub", "qty": 1}
    bot.answer_callback_query(c.id, f"📱 «{b['title'] if b else bid}» savatga qo'shildi!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("add_book_"))
def cb_add_book(c):
    uid = c.from_user.id; bid = int(c.data[9:])
    b = db.get_book(bid)
    carts.setdefault(uid, {})[bid] = {"type": "book", "qty": 1}
    bot.answer_callback_query(c.id, f"📦 «{b['title'] if b else bid}» savatga qo'shildi!")

# ══════════════════════════════════════════════
#  NAMUNA / YUKLAB OLISH
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("preview_"))
def cb_preview(c):
    bid = int(c.data[8:]); b = db.get_book(bid)
    bot.answer_callback_query(c.id)
    if not b or not b.get("preview"):
        bot.send_message(c.message.chat.id, "❌ Namuna mavjud emas."); return
    bot.send_message(c.message.chat.id,
        f"👁 *«{b['title']}» — Namuna*\n\n🔗 [Yuklab olish]({b['preview']})\n\n{PDF_APPS}",
        disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("download_"))
def cb_download(c):
    uid = c.from_user.id; bid = int(c.data[9:])
    if bid not in db.get_purchased(uid):
        bot.answer_callback_query(c.id, "⛔ Bu kitob sizda yo'q!", show_alert=True); return
    b = db.get_book(bid); bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id,
        f"📱 *{b['title']}*\n✍️ {b['author']}\n\n"
        f"🔗 [PDF yuklab olish]({b['epub_url']})\n💾 {b['size_mb']}\n\n{PDF_APPS}",
        disable_web_page_preview=True)

# ══════════════════════════════════════════════
#  ISTAKLAR
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("wish_"))
def cb_wish(c):
    uid = c.from_user.id; bid = int(c.data[5:])
    added = db.toggle_wishlist(uid, bid)
    bot.answer_callback_query(c.id, "❤️ Istakka qo'shildi!" if added else "💔 Istakdan olib tashlandi")

@bot.message_handler(func=lambda m: m.text == "❤️ Istaklar")
def show_wishlist(m):
    uid = m.chat.id; wl = db.get_wishlist(uid)
    if not wl:
        bot.send_message(uid, "❤️ *Istaklar ro'yxati bo'sh.*", reply_markup=main_kb()); return
    owned = db.get_purchased(uid)
    kb = types.InlineKeyboardMarkup(row_width=1)
    txt = "❤️ *Sevimli kitoblarim:*\n\n"
    for bid in wl:
        b = db.get_book(bid)
        if not b: continue
        txt += f"{'✅' if bid in owned else '📚'} *{b['title']}* — {fmt(b['price_epub'])}\n"
        if bid not in owned:
            kb.add(types.InlineKeyboardButton(f"📖 {b['title'][:30]}", callback_data=f"book_paid_{bid}"))
    bot.send_message(uid, txt, reply_markup=kb)

# ══════════════════════════════════════════════
#  SAVATCHA
# ══════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "🛒 Savatcha")
def show_cart(m):
    uid = m.chat.id; ct = carts.get(uid, {})
    if not ct:
        bot.send_message(uid, "🛒 *Savatcha bo'sh!*", reply_markup=main_kb()); return
    txt = "🛒 *Savatcham:*\n\n"
    kb  = types.InlineKeyboardMarkup(row_width=1)
    for bid, item in ct.items():
        b = db.get_book(bid)
        if not b: continue
        icon = "📱 PDF" if item["type"] == "epub" else "📦 Qog'oz"
        txt += f"*{b['title']}*\n   {icon} — {fmt(get_price(bid, item['type']))}\n\n"
        kb.add(types.InlineKeyboardButton(f"❌ {b['title'][:25]}", callback_data=f"remove_{bid}"))
    txt += f"{'─'*24}\n💰 *Jami: {fmt(cart_total(uid))}*"
    kb.add(types.InlineKeyboardButton("🗑 Savatni tozalash", callback_data="cart_clear"))
    kb.add(types.InlineKeyboardButton("💳 Buyurtma berish",  callback_data="checkout"))
    bot.send_message(uid, txt, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("remove_"))
def cb_remove(c):
    uid = c.from_user.id; bid = int(c.data[7:])
    carts.get(uid, {}).pop(bid, None)
    bot.answer_callback_query(c.id, "❌ Olib tashlandi")
    ct = carts.get(uid, {})
    if not ct:
        bot.edit_message_text("🛒 *Savatcha bo'sh!*", c.message.chat.id, c.message.message_id); return
    txt = "🛒 *Savatcham:*\n\n"
    kb  = types.InlineKeyboardMarkup(row_width=1)
    for b_id, item in ct.items():
        b = db.get_book(b_id)
        if not b: continue
        icon = "📱 PDF" if item["type"] == "epub" else "📦 Qog'oz"
        txt += f"*{b['title']}*\n   {icon} — {fmt(get_price(b_id, item['type']))}\n\n"
        kb.add(types.InlineKeyboardButton(f"❌ {b['title'][:25]}", callback_data=f"remove_{b_id}"))
    txt += f"{'─'*24}\n💰 *Jami: {fmt(cart_total(uid))}*"
    kb.add(types.InlineKeyboardButton("🗑 Savatni tozalash", callback_data="cart_clear"))
    kb.add(types.InlineKeyboardButton("💳 Buyurtma berish",  callback_data="checkout"))
    try: bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except: pass

@bot.callback_query_handler(func=lambda c: c.data == "cart_clear")
def cb_cart_clear(c):
    carts.pop(c.from_user.id, None)
    bot.answer_callback_query(c.id, "🗑 Tozalandi!")
    bot.edit_message_text("🛒 Savatcha tozalandi.", c.message.chat.id, c.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "noop")
def cb_noop(c): bot.answer_callback_query(c.id)

# ══════════════════════════════════════════════
#  BUYURTMA — TO'LOV
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data == "checkout")
def cb_checkout(c):
    uid = c.from_user.id; ct = carts.get(uid, {})
    if not ct:
        bot.answer_callback_query(c.id, "Savatcha bo'sh!"); return

    has_physical = any(item["type"] == "book" for item in ct.values())

    if has_physical:
        states[uid] = {"step": "awaiting_address", "ct": dict(ct), "name": c.from_user.first_name}
        carts.pop(uid, None)
        bot.answer_callback_query(c.id)
        bot.send_message(uid,
            "📦 *Qog'oz kitob yetkazib berish*\n\n"
            "📍 Yetkazib berish manzilini yozing:\n"
            "_(Shahar, tuman, ko'cha, uy raqami)_\n\n"
            "_(Bekor qilish: /cancel)_"
        )
    else:
        total = cart_total(uid); oid = new_order_id()
        db.create_order(oid, uid, c.from_user.first_name, ct, total,
                        date_str=datetime.now().strftime("%d.%m.%Y %H:%M"))
        carts.pop(uid, None)
        states[uid] = {"step": "awaiting_receipt", "oid": oid}
        bot.edit_message_text(
            f"💳 *To'lov ma'lumotlari*\n\n🧾 Buyurtma: `{oid}`\n💰 Summa: *{fmt(total)}*\n\n"
            f"{'─'*24}\n📲 *Click:* +998 90 123 45 67\n📲 *Payme:* +998 90 123 45 67\n"
            f"🏦 *Karta:* 8600 1234 5678 9012\n{'─'*24}\n\n"
            f"✅ To'lovdan keyin *screenshot* yuboring.\n⏱ Admin ~15 daqiqada tasdiqlaydi.",
            c.message.chat.id, c.message.message_id)

# ─── MANZIL ───────────────────────────────────
@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "awaiting_address")
def receive_address(m):
    if not m.text: return
    states[m.chat.id]["address"] = m.text
    states[m.chat.id]["step"]    = "awaiting_phone"
    bot.send_message(m.chat.id,
        "📱 Telefon raqamingizni kiriting:\n"
        "_(Misol: +998 90 123 45 67)_"
    )

# ─── TELEFON ──────────────────────────────────
@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "awaiting_phone")
def receive_phone(m):
    if not m.text: return
    s     = states[m.chat.id]
    uid   = m.chat.id
    ct    = s["ct"]

    total = sum(get_price(bid, item["type"]) * item.get("qty", 1) for bid, item in ct.items())
    oid   = new_order_id()
    db.create_order(oid, uid, s["name"], ct, total,
                    address=s["address"], phone=m.text,
                    date_str=datetime.now().strftime("%d.%m.%Y %H:%M"))
    states[uid] = {"step": "awaiting_receipt", "oid": oid}

    bot.send_message(uid,
        f"✅ *Ma'lumotlar qabul qilindi!*\n\n"
        f"📍 Manzil: _{s['address']}_\n"
        f"📱 Telefon: {m.text}\n\n"
        f"{'─'*24}\n"
        f"💳 *To'lov ma'lumotlari*\n\n"
        f"🧾 Buyurtma: `{oid}`\n"
        f"💰 Summa: *{fmt(total)}*\n\n"
        f"{'─'*24}\n"
        f"📲 *Click:* +998 90 123 45 67\n"
        f"📲 *Payme:* +998 90 123 45 67\n"
        f"🏦 *Karta:* 8600 1234 5678 9012\n"
        f"{'─'*24}\n\n"
        f"✅ To'lovdan keyin *screenshot* yuboring.\n"
        f"⏱ Admin ~15 daqiqada tasdiqlaydi."
    )

@bot.message_handler(content_types=["photo"],
    func=lambda m: isinstance(states.get(m.chat.id), dict)
                   and states[m.chat.id].get("step") == "awaiting_receipt")
def receive_receipt(m):
    uid = m.chat.id; oid = states[uid]["oid"]
    order = db.get_order(oid)
    if not order:
        bot.send_message(uid, "❌ Buyurtma topilmadi."); return
    db.update_order_receipt(oid, m.photo[-1].file_id)
    states[uid] = None
    bot.send_message(uid, f"✅ *Chek qabul qilindi!*\n\n🧾 `{oid}`\n⏳ Admin tekshirmoqda...",
                     reply_markup=main_kb())
    items = db.get_order_items(oid)
    txt = (f"🔔 *YANGI TO'LOV!*\n\n🧾 `{oid}`\n👤 {order['name']} (`{uid}`)\n"
           f"📅 {order['date']}\n💰 *{fmt(order['total'])}*\n")
    if order.get("address"):
        txt += f"📍 Manzil: _{order['address']}_\n"
    if order.get("phone"):
        txt += f"📱 Telefon: {order['phone']}\n"
    txt += "\n*Kitoblar:*\n"
    for bid, item in items.items():
        b = db.get_book(bid)
        txt += f"  {'📱' if item['type']=='epub' else '📦'} {b['title'] if b else bid} — {fmt(get_price(bid, item['type']))}\n"
    kb_a = types.InlineKeyboardMarkup(row_width=2)
    kb_a.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{oid}"),
             types.InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{oid}"))
    try: bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=txt, reply_markup=kb_a)
    except: pass

# ══════════════════════════════════════════════
#  ADMIN TASDIQLASH
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_") and is_admin(c.from_user.id))
def admin_approve(c):
    oid = c.data[8:]; order = db.get_order(oid)
    if not order:
        bot.answer_callback_query(c.id, "Topilmadi!"); return
    uid = order["uid"]
    db.update_order_status(oid, "✅ Tasdiqlandi")
    bot.send_message(uid, f"🎉 *To'lovingiz tasdiqlandi!*\n🧾 `{oid}`")
    items = db.get_order_items(oid)
    for bid, it in items.items():
        b = db.get_book(bid)
        if not b: continue
        db.add_purchased(uid, bid)
        if it["type"] == "epub":
            bot.send_message(uid,
                f"📱 *{b['title']}*  —  {b['author']}\n\n"
                f"🔗 [PDF yuklab olish]({b['epub_url']})\n💾 {b['size_mb']}\n\n{PDF_APPS}",
                disable_web_page_preview=True)
        if it["type"] == "book" and b.get("stock", 0) > 0:
            db.update_book(bid, stock=b["stock"] - 1)
    bot.send_message(uid, "✨ *Xaridingiz uchun rahmat!*", reply_markup=main_kb())
    bot.answer_callback_query(c.id, "✅ Tasdiqlandi!")
    try:
        bot.edit_message_caption(
            caption=c.message.caption + f"\n\n✅ TASDIQLANDI — {datetime.now().strftime('%H:%M')}",
            chat_id=c.message.chat.id, message_id=c.message.message_id)
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_") and is_admin(c.from_user.id))
def admin_reject(c):
    oid = c.data[7:]; order = db.get_order(oid)
    if not order:
        bot.answer_callback_query(c.id, "Topilmadi!"); return
    uid = order["uid"]
    db.update_order_status(oid, "❌ Rad etildi")
    states[c.from_user.id] = {"step": "reject_reason", "uid": uid, "oid": oid}
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "❌ Rad etish sababini yozing:\n_(yoki /skip)_")

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "reject_reason" and is_admin(m.chat.id))
def admin_reject_reason(m):
    if not m.text: return
    s = states[m.chat.id]; uid = s["uid"]; oid = s["oid"]
    reason = m.text if m.text != "/skip" else "Noma'lum sabab"
    states[m.chat.id] = None
    bot.send_message(uid,
        f"❌ *To'lovingiz tasdiqlanmadi.*\n🧾 `{oid}`\n📌 Sabab: _{reason}_",
        reply_markup=main_kb())
    bot.send_message(m.chat.id, "✅ Yuborildi.", reply_markup=admin_kb())

# ══════════════════════════════════════════════
#  KITOBLARIM
# ══════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📥 Kitoblarim")
def show_my_books(m):
    uid = m.chat.id; owned = db.get_purchased(uid)
    if not owned:
        bot.send_message(uid, "📥 *Kitoblarim*\n\nHali hech qanday kitob sotib olmadingiz.",
                         reply_markup=main_kb()); return
    kb = types.InlineKeyboardMarkup(row_width=1)
    txt = f"📥 *Mening kitoblarim ({len(owned)} ta):*\n\n"
    for bid in owned:
        b = db.get_book(bid)
        if b:
            txt += f"📱 *{b['title']}* — {b['author']}\n"
            kb.add(types.InlineKeyboardButton(f"⬇️ {b['title']}", callback_data=f"download_{bid}"))
    bot.send_message(uid, txt, reply_markup=kb)

# ══════════════════════════════════════════════
#  QIDIRISH
# ══════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "🔍 Qidirish")
def prompt_search(m):
    states[m.chat.id] = "searching"
    bot.send_message(m.chat.id, "🔍 Kitob nomi yoki muallif ismini yozing:",
                     reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: states.get(m.chat.id) == "searching")
def do_search(m):
    if not m.text: return
    q = m.text.lower().strip(); states[m.chat.id] = None
    found = db.search_books(q)
    if not found:
        bot.send_message(m.chat.id, f"❌ *«{m.text}»* bo'yicha hech narsa topilmadi.",
                         reply_markup=main_kb()); return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for bid, b in found.items():
        sec = "free" if b["price_epub"] == 0 else "paid"
        price_txt = "Bepul" if b["price_epub"] == 0 else fmt(b["price_epub"])
        kb.add(types.InlineKeyboardButton(f"📱 {b['title']} — {price_txt}", callback_data=f"book_{sec}_{bid}"))
    bot.send_message(m.chat.id, f"🔍 *{len(found)} ta natija:*", reply_markup=kb)
    bot.send_message(m.chat.id, "Menyu:", reply_markup=main_kb())

# ══════════════════════════════════════════════
#  YORDAM
# ══════════════════════════════════════════════
@bot.message_handler(commands=["help"])
@bot.message_handler(func=lambda m: m.text == "💬 Yordam")
def show_help(m):
    bot.send_message(m.chat.id,
        "💬 *Yordam*\n\n"
        "📱 *Pullik e-kitob:* Kutubxona → Pullik → Savatga → To'lov → Chek → Admin tasdiqlaydi ✅\n\n"
        "🎁 *Bepul e-kitob:* Kutubxona → Bepul → Kitob tanlang → Havola keladi\n\n"
        "📦 *Qog'oz kitob:* Kutubxona → Qog'oz → Savatga → To'lov\n\n"
        f"{PDF_APPS}\n\n📞 *Admin:* @admin  |  ⏰ *Ish vaqti:* 9:00–21:00",
        reply_markup=main_kb())

# ══════════════════════════════════════════════
#  ADMIN PANEL (Telegram)
# ══════════════════════════════════════════════
@bot.message_handler(commands=["admin"])
def cmd_admin(m):
    if not is_admin(m.chat.id):
        bot.send_message(m.chat.id, "⛔ Ruxsat yo'q!"); return
    stats = db.get_stats()
    bot.send_message(m.chat.id,
        f"╔══════════════════════╗\n║   🔐  ADMIN PANEL   ║\n╚══════════════════════╝\n\n"
        f"⏳ Kutayotgan: *{stats['pending']}* ta\n✅ Tasdiqlangan: *{stats['confirmed']}* ta\n"
        f"📚 Kitoblar: *{stats['books_count']}* ta\n💰 Daromad: *{fmt(stats['revenue'])}*",
        reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "⏳ Kutayotgan buyurtmalar" and is_admin(m.chat.id))
def admin_pending(m):
    pending = db.get_orders("⏳")
    if not pending:
        bot.send_message(m.chat.id, "Kutayotgan buyurtma yo'q.", reply_markup=admin_kb()); return
    for o in pending:
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{o['order_id']}"),
               types.InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{o['order_id']}"))
        items = db.get_order_items(o['order_id'])
        txt = f"⏳ *Buyurtma:* `{o['order_id']}`\n👤 {o['name']} (`{o['uid']}`)\n💰 {fmt(o['total'])}  |  📅 {o['date']}\n\n*Kitoblar:*\n"
        for bid, item in items.items():
            b = db.get_book(bid)
            txt += f"  {'📱' if item['type']=='epub' else '📦'} {b['title'] if b else bid}\n"
        bot.send_message(m.chat.id, txt, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "✅ Tasdiqlangan buyurtmalar" and is_admin(m.chat.id))
def admin_confirmed(m):
    confirmed = db.get_orders("✅")
    if not confirmed:
        bot.send_message(m.chat.id, "Hali tasdiqlangan buyurtma yo'q.", reply_markup=admin_kb()); return
    txt = f"✅ *Tasdiqlangan ({len(confirmed)} ta):*\n\n"
    for o in confirmed[:10]:
        txt += f"🧾 `{o['order_id']}` | 👤 `{o['uid']}` | 💰 {fmt(o['total'])} | {o['date']}\n"
    bot.send_message(m.chat.id, txt, reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "👥 Foydalanuvchilar" and is_admin(m.chat.id))
def admin_users(m):
    all_users = db.get_users()
    if not all_users:
        bot.send_message(m.chat.id, "Hali foydalanuvchi yo'q.", reply_markup=admin_kb()); return
    txt = f"👥 *Foydalanuvchilar ({len(all_users)} ta):*\n\n"
    for uid, u in all_users.items():
        cnt = db.get_purchased_count(uid)
        txt += f"👤 `{uid}` — {u['name']} — {cnt} ta kitob\n"
    bot.send_message(m.chat.id, txt, reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and is_admin(m.chat.id))
def admin_stats(m):
    stats = db.get_stats()
    txt = (f"📊 *Statistika*\n\n💰 Daromad: *{fmt(stats['revenue'])}*\n✅ Tasdiqlangan: {stats['confirmed']} ta\n"
           f"⏳ Kutayotgan: {stats['pending']} ta\n"
           f"👥 Foydalanuvchilar: {stats['users_count']} ta\n📚 Kitoblar: {stats['books_count']} ta\n\n🏆 *Top:*\n")
    for bid, title, cnt in stats["top_books"]:
        txt += f"  📱 {title} — {cnt} ta\n"
    bot.send_message(m.chat.id, txt, reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "📢 Xabar yuborish" and is_admin(m.chat.id))
def admin_broadcast_prompt(m):
    states[m.chat.id] = "broadcasting"
    bot.send_message(m.chat.id, "📢 Barcha foydalanuvchilarga xabarni yozing:\n_(Bekor: /cancel)_",
                     reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: states.get(m.chat.id) == "broadcasting" and is_admin(m.chat.id))
def admin_broadcast(m):
    if not m.text: return
    states[m.chat.id] = None
    all_users = db.get_users()
    for uid in all_users:
        try: bot.send_message(uid, f"📢 *Yangilik:*\n\n{m.text}")
        except: pass
    bot.send_message(m.chat.id, f"✅ {len(all_users)} ta foydalanuvchiga yuborildi!", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "🔙 Asosiy menyu" and is_admin(m.chat.id))
def admin_back(m):
    bot.send_message(m.chat.id, "Asosiy menyu:", reply_markup=main_kb())

# ══════════════════════════════════════════════
#  KITOBLAR BAZASI (Telegram admin)
# ══════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📖 Kitoblar bazasi" and is_admin(m.chat.id))
def admin_books_menu(m):
    bot.send_message(m.chat.id, "📖 Kitoblar bazasini boshqarish:", reply_markup=admin_books_kb())

@bot.message_handler(func=lambda m: m.text == "🔙 Admin Panel" and is_admin(m.chat.id))
def admin_back_panel(m):
    bot.send_message(m.chat.id, "Admin Panel:", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "➕ Yangi kitob" and is_admin(m.chat.id))
def admin_add_start(m):
    states[m.chat.id] = {"step": "add_title"}
    bot.send_message(m.chat.id, "Sarlavha yozing:\n_(Bekor: /cancel)_",
                     reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_title" and is_admin(m.chat.id))
def add_title(m):
    if not m.text: return
    states[m.chat.id].update({"title": m.text, "step": "add_author"})
    bot.send_message(m.chat.id, "Muallifni kiriting:")

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_author" and is_admin(m.chat.id))
def add_author(m):
    if not m.text: return
    states[m.chat.id].update({"author": m.text, "step": "add_price_epub"})
    bot.send_message(m.chat.id, "E-kitob narxini kiriting (0 = bepul):")

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_price_epub" and is_admin(m.chat.id))
def add_price_epub(m):
    if not m.text or not m.text.isdigit():
        bot.send_message(m.chat.id, "Faqat raqam!"); return
    states[m.chat.id].update({"price_epub": int(m.text), "step": "add_price_book"})
    bot.send_message(m.chat.id, "Qog'oz narxini kiriting (0 = yo'q):")

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_price_book" and is_admin(m.chat.id))
def add_price_book(m):
    if not m.text or not m.text.isdigit():
        bot.send_message(m.chat.id, "Faqat raqam!"); return
    pb = int(m.text)
    categories = db.get_categories()
    states[m.chat.id].update({"price_book": pb, "has_physical": pb > 0})
    if pb > 0:
        states[m.chat.id]["step"] = "add_stock"
        bot.send_message(m.chat.id, "Ombor sonini kiriting:")
    else:
        states[m.chat.id].update({"stock": 0, "step": "add_cat"})
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for k in categories: kb.add(k)
        bot.send_message(m.chat.id, "Kategoriyani tanlang:", reply_markup=kb)

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_stock" and is_admin(m.chat.id))
def add_stock(m):
    if not m.text or not m.text.isdigit(): return
    categories = db.get_categories()
    states[m.chat.id].update({"stock": int(m.text), "step": "add_cat"})
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for k in categories: kb.add(k)
    bot.send_message(m.chat.id, "Kategoriyani tanlang:", reply_markup=kb)

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_cat" and is_admin(m.chat.id))
def add_cat(m):
    categories = db.get_categories()
    if m.text not in categories:
        bot.send_message(m.chat.id, "Tugmalardan tanlang."); return
    states[m.chat.id].update({"cat": m.text, "step": "add_desc"})
    bot.send_message(m.chat.id, "Tavsif yozing:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_desc" and is_admin(m.chat.id))
def add_desc(m):
    if not m.text: return
    states[m.chat.id].update({"desc": m.text, "step": "add_epub_url"})
    bot.send_message(m.chat.id, "PDF havolasini kiriting:")

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "add_epub_url" and is_admin(m.chat.id))
def add_epub_url(m):
    if not m.text: return
    s = states[m.chat.id]
    db.add_book(
        title=s["title"], author=s["author"],
        price_epub=s["price_epub"], price_book=s["price_book"],
        cat=s["cat"], desc=s["desc"], epub_url=m.text,
        has_physical=s["has_physical"], stock=s.get("stock", 0)
    )
    states[m.chat.id] = None
    bot.send_message(m.chat.id, f"✅ *{s['title']}* qo'shildi!", reply_markup=admin_books_kb())

@bot.message_handler(func=lambda m: m.text == "✏️ Tahrirlash" and is_admin(m.chat.id))
def admin_edit(m):
    books = db.get_books()
    if not books:
        bot.send_message(m.chat.id, "Baza bo'sh.", reply_markup=admin_books_kb()); return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for bid, b in books.items():
        kb.add(types.InlineKeyboardButton(f"✏️ {b['title']}", callback_data=f"adm_edt_{bid}"))
    bot.send_message(m.chat.id, "Tahrirlanadigan kitobni tanlang:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_edt_") and is_admin(c.from_user.id))
def cb_edit(c):
    bid = int(c.data[8:])
    states[c.message.chat.id] = {"step": "edit_field", "bid": bid}
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("Narxi (EPUB)", "Narxi (Qog'oz)", "Ombor soni", "PDF havola", "Bekor qilish")
    bot.send_message(c.message.chat.id, "Nimasini o'zgartirmoqchisiz?", reply_markup=kb)

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "edit_field" and is_admin(m.chat.id))
def edit_field(m):
    if not m.text: return
    if m.text == "Bekor qilish":
        states[m.chat.id] = None
        bot.send_message(m.chat.id, "Bekor qilindi.", reply_markup=admin_books_kb()); return
    states[m.chat.id].update({"field": m.text, "step": "edit_value"})
    bot.send_message(m.chat.id, f"{m.text} uchun yangi qiymat:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: isinstance(states.get(m.chat.id), dict)
                     and states[m.chat.id].get("step") == "edit_value" and is_admin(m.chat.id))
def edit_value(m):
    if not m.text: return
    s = states[m.chat.id]; bid = s["bid"]; field = s["field"]
    states[m.chat.id] = None
    field_map = {"Narxi (EPUB)": ("price_epub", int), "Narxi (Qog'oz)": ("price_book", int),
                 "Ombor soni": ("stock", int), "PDF havola": ("epub_url", str)}
    if field not in field_map:
        bot.send_message(m.chat.id, "❌ Xato.", reply_markup=admin_books_kb()); return
    key, cast = field_map[field]
    try:
        db.update_book(bid, **{key: cast(m.text)})
        bot.send_message(m.chat.id, "✅ Saqlandi!", reply_markup=admin_books_kb())
    except:
        bot.send_message(m.chat.id, "❌ Xato!", reply_markup=admin_books_kb())

@bot.message_handler(func=lambda m: m.text == "🗑 O'chirish" and is_admin(m.chat.id))
def admin_delete(m):
    books = db.get_books()
    if not books:
        bot.send_message(m.chat.id, "Baza bo'sh.", reply_markup=admin_books_kb()); return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for bid, b in books.items():
        kb.add(types.InlineKeyboardButton(f"🗑 {b['title']}", callback_data=f"adm_del_{bid}"))
    bot.send_message(m.chat.id, "O'chiriladigan kitobni tanlang:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_") and is_admin(c.from_user.id))
def cb_delete(c):
    bid = int(c.data[8:]); b = db.get_book(bid)
    title = b["title"] if b else "Kitob"
    db.delete_book(bid)
    bot.answer_callback_query(c.id, f"🗑 «{title}» o'chirildi!", show_alert=True)
    bot.delete_message(c.message.chat.id, c.message.message_id)

# ══════════════════════════════════════════════
#  /cancel  /skip  — NOMA'LUM
# ══════════════════════════════════════════════
@bot.message_handler(commands=["cancel", "skip"])
def cmd_cancel(m):
    states[m.chat.id] = None
    bot.send_message(m.chat.id, "Bekor qilindi.", reply_markup=main_kb())

@bot.message_handler(func=lambda m: True)
def unknown(m):
    if is_admin(m.chat.id): return
    bot.send_message(m.chat.id, "🤔 Menyudan foydalaning:", reply_markup=main_kb())

# ══════════════════════════════════════════════
#  ISHGA TUSHIRISH
# ══════════════════════════════════════════════
if __name__ == "__main__":
    print("╔══════════════════════════════╗")
    print("║  📱 KITOB DUNYOSI — Ishga    ║")
    print("║     tushdi!                  ║")
    print("╚══════════════════════════════╝")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
