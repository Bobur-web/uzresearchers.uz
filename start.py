"""
╔══════════════════════════════════════════════════════════╗
║  🚀  START  —  Bot + Admin Panel birga ishga tushirish  ║
╚══════════════════════════════════════════════════════════╝

Ishga tushirish:
    python start.py
"""

import threading
import os
import sys
import database as db

def run_bot():
    """Telegram botni ishga tushirish."""
    print("[BOT] Ishga tushmoqda...")
    import filolog
    filolog.bot.infinity_polling(timeout=30, long_polling_timeout=20)

def run_admin():
    """Admin panelni ishga tushirish."""
    port = int(os.getenv("PORT", 5000))
    print(f"[ADMIN] Ishga tushmoqda (port {port})...")
    import admin_app
    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", port, admin_app.app, use_reloader=False)

if __name__ == "__main__":
    print("=" * 40)
    print("  KITOB DUNYOSI — Full Start")
    print("  Bot + Admin Panel")
    print("=" * 40)

    # DB ni bir marta main threadda ishga tushirish (race condition oldini olish)
    db.init_db()
    db.seed_defaults()
    print("[DB] Baza tayyor.")

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    admin_thread = threading.Thread(target=run_admin, daemon=True)

    bot_thread.start()
    admin_thread.start()

    try:
        bot_thread.join()
    except KeyboardInterrupt:
        print("\n[STOP] To'xtatildi.")
        sys.exit(0)
