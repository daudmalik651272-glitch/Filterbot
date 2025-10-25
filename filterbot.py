#!/usr/bin/env python3
# ⚡ Ultimate Filter Bot v7.0 (Full DM↔GC Sync + Multi-Admin + Multi-Button, Vertical Buttons)
# ✅ /connect | /disconnect | /filter | /filters | /stop | /stop_all | /button
# ✅ Multi-admin shared DB | Inline buttons vertical | Sticker/Text/Photo/Video supported

import os, sqlite3, telebot, json, html, re
from telebot import types

TOKEN = os.getenv("TG_FILTER_BOT_TOKEN") or "8379241953:AAFKG9tlUBuogez5qR7RfUdd2zLzXxMvnnk"
DB_FILE = "filters.db"
bot = telebot.TeleBot(TOKEN, parse_mode=None)

DEV_NAME = "👑 Developer"
DEV_URL = "https://t.me/Apni_aukat_me_raho786"
SUPPORT_NAME = "💬 Support GC"
SUPPORT_URL = "https://t.me/Anime_Group_x_x"

# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            trigger TEXT NOT NULL,
            reply_type TEXT,
            reply_text TEXT,
            file_id TEXT,
            markup TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            user_id TEXT UNIQUE,
            chat_id TEXT
        )
    """)
    conn.commit()
    return conn

DB = init_db()

# ---------------- DB FUNCTIONS ----------------
def db_add_filter(chat_id, trigger, reply_type, reply_text=None, file_id=None, markup=None):
    cur = DB.cursor()
    cur.execute("SELECT id FROM filters WHERE chat_id=? AND lower(trigger)=lower(?)", (str(chat_id), trigger))
    if cur.fetchone():
        cur.execute("UPDATE filters SET reply_type=?, reply_text=?, file_id=?, markup=? WHERE chat_id=? AND lower(trigger)=lower(?)",
                    (reply_type, reply_text, file_id, markup, str(chat_id), trigger))
    else:
        cur.execute("INSERT INTO filters (chat_id, trigger, reply_type, reply_text, file_id, markup) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(chat_id), trigger, reply_type, reply_text, file_id, markup))
    DB.commit()

def db_remove_filter(chat_id, trigger):
    cur = DB.cursor()
    cur.execute("DELETE FROM filters WHERE chat_id=? AND lower(trigger)=lower(?)", (str(chat_id), trigger))
    DB.commit()
    return cur.rowcount > 0

def db_clear_filters(chat_id):
    cur = DB.cursor()
    cur.execute("DELETE FROM filters WHERE chat_id=?", (str(chat_id),))
    DB.commit()

def db_list_filters(chat_id):
    cur = DB.cursor()
    cur.execute("SELECT trigger FROM filters WHERE chat_id=?", (str(chat_id),))
    return [r[0] for r in cur.fetchall()]

def db_connect(user_id, chat_id):
    cur = DB.cursor()
    cur.execute("INSERT OR REPLACE INTO connections (user_id, chat_id) VALUES (?, ?)", (str(user_id), str(chat_id)))
    DB.commit()

def db_disconnect(user_id):
    cur = DB.cursor()
    cur.execute("DELETE FROM connections WHERE user_id=?", (str(user_id),))
    DB.commit()

def db_get_connection(user_id):
    cur = DB.cursor()
    cur.execute("SELECT chat_id FROM connections WHERE user_id=?", (str(user_id),))
    r = cur.fetchone()
    return r[0] if r else None

# ---------------- UTILS ----------------
def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

def extract_markup(msg):
    if not msg.reply_markup:
        return None
    try:
        data = []
        for row in msg.reply_markup.inline_keyboard:
            # Make sure to store as vertical (one button per row)
            for b in row:
                if b.url:
                    data.append([{"text": b.text, "url": b.url}])
        return json.dumps(data)
    except Exception as e:
        print("extract_markup error:", e)
        return None

def rebuild_markup(markup_json):
    if not markup_json:
        return None
    try:
        data = json.loads(markup_json)
        mk = types.InlineKeyboardMarkup()
        # Always vertical layout
        for row in data:
            for b in row:
                mk.add(types.InlineKeyboardButton(text=b["text"], url=b["url"]))
        return mk
    except Exception as e:
        print("rebuild_markup error:", e)
        return None

# ---------------- COMMANDS ----------------
@bot.message_handler(commands=['start'])
def start(msg):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(DEV_NAME, url=DEV_URL),
               types.InlineKeyboardButton(SUPPORT_NAME, url=SUPPORT_URL))
    bot.reply_to(msg, (
        "👋 *Ultimate Filter Bot v7.0*\n\n"
        "`/connect` — link your group\n"
        "`/disconnect` — unlink\n"
        "`/filter <word>` — add filter\n"
        "`/button '<word>' TEXT|URL [more buttons]`\n"
        "`/stop <word>` — delete one\n"
        "`/stop_all` — delete all\n"
        "`/filters` — list filters\n\n"
    ), parse_mode="Markdown", reply_markup=markup)

# ---------------- CONNECT / DISCONNECT ----------------
@bot.message_handler(commands=['connect'])
def connect(msg):
    if msg.chat.type != "private":
        if not is_admin(msg.chat.id, msg.from_user.id):
            bot.reply_to(msg, "⚠️ Only admins can connect this group.")
            return
        db_connect(msg.from_user.id, msg.chat.id)
        bot.reply_to(msg, f"✅ Connected *{msg.chat.title}* to your DM.", parse_mode="Markdown")
    else:
        bot.reply_to(msg, "📎 Use /connect inside your group or forward a group message here.")

@bot.message_handler(func=lambda m: m.forward_from_chat and m.chat.type == "private")
def connect_forward(msg):
    chat = msg.forward_from_chat
    if not is_admin(chat.id, msg.from_user.id):
        bot.reply_to(msg, "⚠️ You must be admin there.")
        return
    db_connect(msg.from_user.id, chat.id)
    bot.reply_to(msg, f"✅ Connected with *{chat.title}*", parse_mode="Markdown")

@bot.message_handler(commands=['disconnect'])
def disconnect(msg):
    db_disconnect(msg.from_user.id)
    bot.reply_to(msg, "🔌 Disconnected successfully.")

# ---------------- FILTER ADD ----------------
@bot.message_handler(commands=['filter'])
def add_filter(msg):
    user_id, chat_id = msg.from_user.id, msg.chat.id
    target = chat_id if msg.chat.type != "private" else db_get_connection(user_id)
    if not target:
        bot.reply_to(msg, "⚠️ Connect a group first with /connect.")
        return
    if msg.chat.type != "private" and not is_admin(chat_id, user_id):
        bot.reply_to(msg, "⚠️ Only admins can add filters.")
        return
    if not msg.reply_to_message:
        bot.reply_to(msg, "📎 Reply to a message with `/filter <word>`", parse_mode="Markdown")
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: `/filter <word>`", parse_mode="Markdown")
        return

    trigger = parts[1].strip().lower()
    r = msg.reply_to_message
    markup = extract_markup(r)
    reply_type, reply_text, file_id = None, None, None

    if r.text:
        reply_type, reply_text = "text", html.escape(r.text)
    elif r.photo:
        reply_type, file_id = "photo", r.photo[-1].file_id
    elif r.video:
        reply_type, file_id = "video", r.video.file_id
    elif r.sticker:
        reply_type, file_id = "sticker", r.sticker.file_id
    else:
        bot.reply_to(msg, "❌ Unsupported message type.")
        return

    db_add_filter(target, trigger, reply_type, reply_text, file_id, markup)
    bot.reply_to(msg, f"✅ Filter '{trigger}' added successfully!")

# ---------------- BUTTON ADD ----------------
@bot.message_handler(commands=['button'])
def add_button(msg):
    if not msg.reply_to_message:
        bot.reply_to(msg, "📎 Reply with `/button '<word>' TEXT|URL`", parse_mode="Markdown")
        return

    text = msg.text
    m = re.search(r"'(.*?)'\s+(.*)", text)
    if not m:
        bot.reply_to(msg, "⚠️ Format:\n`/button 'hello' TEXT|URL TEXT|URL`", parse_mode="Markdown")
        return

    trigger = m.group(1).strip().lower()
    btns = re.findall(r"([^|]+)\|(\S+)", m.group(2))
    if not btns:
        bot.reply_to(msg, "⚠️ Invalid format!", parse_mode="Markdown")
        return

    # vertical button layout (each in new line)
    markup_data = [[{"text": t.strip(), "url": u.strip()}] for t, u in btns]
    markup_json = json.dumps(markup_data)

    r = msg.reply_to_message
    reply_type, reply_text, file_id = None, None, None
    if r.text:
        reply_type, reply_text = "text", html.escape(r.text)
    elif r.sticker:
        reply_type, file_id = "sticker", r.sticker.file_id
    elif r.photo:
        reply_type, file_id = "photo", r.photo[-1].file_id
    elif r.video:
        reply_type, file_id = "video", r.video.file_id
    else:
        bot.reply_to(msg, "⚠️ Unsupported message type.")
        return

    user_id = msg.from_user.id
    target = msg.chat.id if msg.chat.type != "private" else db_get_connection(user_id)
    if not target:
        bot.reply_to(msg, "⚠️ Connect a group first.")
        return

    db_add_filter(target, trigger, reply_type, reply_text, file_id, markup_json)
    mk = rebuild_markup(markup_json)

    if reply_type == "text":
        bot.send_message(msg.chat.id, html.unescape(reply_text), reply_markup=mk)
    elif reply_type == "sticker":
        bot.send_sticker(msg.chat.id, file_id, reply_markup=mk)
    elif reply_type == "photo":
        bot.send_photo(msg.chat.id, file_id, reply_markup=mk)
    elif reply_type == "video":
        bot.send_video(msg.chat.id, file_id, reply_markup=mk)
    bot.reply_to(msg, f"✅ Buttons added for '{trigger}'!")

# ---------------- STOP / LIST / TRIGGERS (unchanged) ----------------
@bot.message_handler(commands=['stop'])
def stop_filter(msg):
    user_id, chat_id = msg.from_user.id, msg.chat.id
    target = chat_id if msg.chat.type != "private" else db_get_connection(user_id)
    if not target:
        bot.reply_to(msg, "⚠️ Connect first.")
        return
    if msg.chat.type != "private" and not is_admin(chat_id, user_id):
        bot.reply_to(msg, "⚠️ Admins only.")
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: `/stop <word>`", parse_mode="Markdown")
        return
    trigger = parts[1].strip().lower()
    deleted = db_remove_filter(target, trigger)
    bot.reply_to(msg, f"🗑️ Filter '{trigger}' deleted." if deleted else f"⚠️ Not found.")

@bot.message_handler(commands=['stop_all'])
def stop_all(msg):
    user_id, chat_id = msg.from_user.id, msg.chat.id
    target = chat_id if msg.chat.type != "private" else db_get_connection(user_id)
    if not target:
        bot.reply_to(msg, "⚠️ Connect first.")
        return
    if msg.chat.type != "private" and not is_admin(chat_id, user_id):
        bot.reply_to(msg, "⚠️ Admins only.")
        return
    db_clear_filters(target)
    bot.reply_to(msg, "🧹 All filters cleared!")

@bot.message_handler(commands=['filters'])
def list_filters(msg):
    chat_id = msg.chat.id
    if msg.chat.type == "private":
        conn = db_get_connection(msg.from_user.id)
        if conn:
            chat_id = conn
        else:
            bot.reply_to(msg, "⚠️ Connect first.")
            return
    fl = db_list_filters(chat_id)
    bot.reply_to(msg, "📋 *Filters:*\n" + "\n".join([f"• {x}" for x in fl]) if fl else "📭 No filters.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True, content_types=["text", "sticker"])
def trigger(msg):
    try:
        chat_id = str(msg.chat.id)
        text = msg.text.lower().strip() if msg.text else (msg.sticker.emoji or "")
        if not text:
            return
        cur = DB.cursor()
        cur.execute("SELECT trigger, reply_type, reply_text, file_id, markup FROM filters WHERE chat_id=?", (chat_id,))
        for trig, typ, txt, fid, markup_json in cur.fetchall():
            if text == trig:
                mk = rebuild_markup(markup_json)
                if typ == "text":
                    bot.send_message(chat_id, html.unescape(txt or ""), reply_markup=mk)
                elif typ == "sticker":
                    bot.send_sticker(chat_id, fid, reply_markup=mk)
                elif typ == "photo":
                    bot.send_photo(chat_id, fid, reply_markup=mk)
                elif typ == "video":
                    bot.send_video(chat_id, fid, reply_markup=mk)
                break
    except Exception as e:
        print("⚠️ Trigger error:", e)

print("🤖 Filter Bot Running)")
bot.infinity_polling()
