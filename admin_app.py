"""
╔══════════════════════════════════════════════════════════╗
║         🌐  ADMIN PANEL  —  Flask Web Ilova             ║
║         Kitoblar, Buyurtmalar, Foydalanuvchilar CRUD    ║
╚══════════════════════════════════════════════════════════╝
"""

import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import database as db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "kitob-dunyosi-secret-key-2024")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Baza start.py orqali ishga tushiriladi


# ══════════════════════════════════════════════
#  AUTENTIFIKATSIYA
# ══════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("Muvaffaqiyatli kirdingiz!", "success")
            return redirect(url_for("dashboard"))
        flash("Parol noto'g'ri!", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


# ══════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════
@app.route("/")
@login_required
def dashboard():
    stats = db.get_stats()
    recent_orders = db.get_orders()[:5]
    return render_template("dashboard.html", stats=stats, recent_orders=recent_orders)


# ══════════════════════════════════════════════
#  KITOBLAR CRUD
# ══════════════════════════════════════════════
@app.route("/books")
@login_required
def books_list():
    books = db.get_books()
    categories = db.get_categories()
    return render_template("books.html", books=books, categories=categories)


@app.route("/books/add", methods=["GET", "POST"])
@login_required
def book_add():
    categories = db.get_categories()
    if request.method == "POST":
        f = request.form
        db.add_book(
            title=f["title"], author=f["author"],
            price_epub=int(f.get("price_epub", 0) or 0),
            price_book=int(f.get("price_book", 0) or 0),
            cat=f.get("cat", ""),
            desc=f.get("desc", ""),
            epub_url=f.get("epub_url", ""),
            preview=f.get("preview", ""),
            size_mb=f.get("size_mb", "1 MB"),
            pages=int(f.get("pages", 0) or 0),
            year=int(f.get("year", 2024) or 2024),
            rating=float(f.get("rating", 5.0) or 5.0),
            badge=f.get("badge", ""),
            has_physical=bool(f.get("has_physical")),
            stock=int(f.get("stock", 0) or 0),
        )
        flash(f"«{f['title']}» muvaffaqiyatli qo'shildi!", "success")
        return redirect(url_for("books_list"))
    return render_template("book_form.html", book=None, categories=categories, action="add")


@app.route("/books/edit/<int:bid>", methods=["GET", "POST"])
@login_required
def book_edit(bid):
    book = db.get_book(bid)
    if not book:
        flash("Kitob topilmadi!", "error")
        return redirect(url_for("books_list"))
    categories = db.get_categories()
    if request.method == "POST":
        f = request.form
        db.update_book(bid,
            title=f["title"], author=f["author"],
            price_epub=int(f.get("price_epub", 0) or 0),
            price_book=int(f.get("price_book", 0) or 0),
            cat=f.get("cat", ""),
            desc=f.get("desc", ""),
            epub_url=f.get("epub_url", ""),
            preview=f.get("preview", ""),
            size_mb=f.get("size_mb", "1 MB"),
            pages=int(f.get("pages", 0) or 0),
            year=int(f.get("year", 2024) or 2024),
            rating=float(f.get("rating", 5.0) or 5.0),
            badge=f.get("badge", ""),
            has_physical=bool(f.get("has_physical")),
            stock=int(f.get("stock", 0) or 0),
        )
        flash(f"«{f['title']}» muvaffaqiyatli tahrirlandi!", "success")
        return redirect(url_for("books_list"))
    return render_template("book_form.html", book=book, categories=categories, action="edit")


@app.route("/books/delete/<int:bid>", methods=["POST"])
@login_required
def book_delete(bid):
    book = db.get_book(bid)
    title = book["title"] if book else "Kitob"
    db.delete_book(bid)
    flash(f"«{title}» o'chirildi!", "success")
    return redirect(url_for("books_list"))


# ══════════════════════════════════════════════
#  KATEGORIYALAR CRUD
# ══════════════════════════════════════════════
@app.route("/categories")
@login_required
def categories_list():
    categories = db.get_categories()
    books = db.get_books()
    cat_counts = {}
    for b in books.values():
        c = b.get("cat", "")
        if c:
            cat_counts[c] = cat_counts.get(c, 0) + 1
    return render_template("categories.html", categories=categories, cat_counts=cat_counts)


@app.route("/categories/add", methods=["POST"])
@login_required
def category_add():
    key = request.form.get("key", "").strip().lower()
    emoji = request.form.get("emoji", "📚").strip()
    label = request.form.get("label", "").strip()
    if key and label:
        db.add_category(key, emoji, label)
        flash(f"«{label}» kategoriya qo'shildi!", "success")
    else:
        flash("Barcha maydonlarni to'ldiring!", "error")
    return redirect(url_for("categories_list"))


@app.route("/categories/edit/<key>", methods=["POST"])
@login_required
def category_edit(key):
    new_key = request.form.get("key", "").strip().lower()
    emoji = request.form.get("emoji", "📚").strip()
    label = request.form.get("label", "").strip()
    if new_key and label:
        db.update_category(key, new_key, emoji, label)
        flash(f"Kategoriya tahrirlandi!", "success")
    else:
        flash("Barcha maydonlarni to'ldiring!", "error")
    return redirect(url_for("categories_list"))


@app.route("/categories/delete/<key>", methods=["POST"])
@login_required
def category_delete(key):
    cat = db.get_category(key)
    label = cat["label"] if cat else key
    db.delete_category(key)
    flash(f"«{label}» o'chirildi!", "success")
    return redirect(url_for("categories_list"))


# ══════════════════════════════════════════════
#  BUYURTMALAR
# ══════════════════════════════════════════════
@app.route("/orders")
@login_required
def orders_list():
    status_filter = request.args.get("status", "")
    if status_filter:
        all_orders = db.get_orders(status_filter)
    else:
        all_orders = db.get_orders()
    return render_template("orders.html", orders=all_orders, status_filter=status_filter)


@app.route("/orders/<oid>")
@login_required
def order_detail(oid):
    order = db.get_order(oid)
    if not order:
        flash("Buyurtma topilmadi!", "error")
        return redirect(url_for("orders_list"))
    items = db.get_order_items(oid)
    books_info = {}
    for bid in items:
        books_info[bid] = db.get_book(bid)
    return render_template("order_detail.html", order=order, items=items, books_info=books_info)


@app.route("/orders/<oid>/status", methods=["POST"])
@login_required
def order_status_update(oid):
    status = request.form.get("status", "")
    db.update_order_status(oid, status)
    flash(f"Buyurtma holati yangilandi: {status}", "success")
    return redirect(url_for("order_detail", oid=oid))


@app.route("/orders/<oid>/delete", methods=["POST"])
@login_required
def order_delete(oid):
    db.delete_order(oid)
    flash("Buyurtma o'chirildi!", "success")
    return redirect(url_for("orders_list"))


# ══════════════════════════════════════════════
#  FOYDALANUVCHILAR
# ══════════════════════════════════════════════
@app.route("/users")
@login_required
def users_list():
    all_users = db.get_users()
    user_stats = {}
    for uid in all_users:
        user_stats[uid] = {
            "purchased": db.get_purchased_count(uid),
            "wishlist": len(db.get_wishlist(uid)),
        }
    return render_template("users.html", users=all_users, user_stats=user_stats)


# ══════════════════════════════════════════════
#  YORDAMCHI — FORMAT FILTR
# ══════════════════════════════════════════════
@app.template_filter("fmt_price")
def fmt_price(n):
    return f"{n:,}".replace(",", " ") + " so'm"


if __name__ == "__main__":
    print("[ADMIN] Panel: http://localhost:5000")
    print("[ADMIN] Parol:", ADMIN_PASSWORD)
    app.run(host="0.0.0.0", port=5000, debug=True)
