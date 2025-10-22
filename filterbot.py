#!/usr/bin/env python3
# 🔥 Ultimate Filter Bot (Unlimited + OG Message + Buttons + Stickers)
# ✅ Termux Compatible | Rose-Style Feature System
# By ChatGPT (custom for bhai)

import os
import sqlite3
import telebot
from telebot import types
import json
import html

TOKEN = os.getenv("TG_FILTER_BOT_TOKEN") or "8379241953:AAFKG9tlUBuogez5qR7RfUdd2zLzXxMvnnk"
DB_FILE = "ultimate_filters.db"

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# ------------------ DATABASE ------------------
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
            user_id TEXT PRIMARY KEY,
            chat_id TEXT
        )
    """)
    try:
        cur.execute("ALTER TABLE filters ADD COLUMN markup TEXT")
    except:
        pass
    conn.commit()
    return conn

DB = init_db()

# ------------------ DB FUNCTIONS ------------------
def db_add_filter(chat_id, trigger, reply_type, reply_text=None, file_id=None, markup=None):
    cur = DB.cursor()
    cur.execute("SELECT id FROM filters WHERE chat_id=? AND lower(trigger)=lower(?)", (str(chat_id), trigger))
    if cur.fetchone():
        return False
    cur.execute("""
        INSERT INTO filters (chat_id, trigger, reply_type, reply_text, file_id, markup)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(chat_id), trigger, reply_type, reply_text, file_id, markup))
    DB.commit()
    return True

def db_remove_filter(chat_id, trigger):
    cur = DB.cursor()
    cur.execute("DELETE FROM filters WHERE chat_id=? AND lower(trigger)=lower(?)", (str(chat_id), trigger))
    DB.commit()
    return cur.rowcount > 0

def db_list_filters(chat_id):
    cur = DB.cursor()
    cur.execute("SELECT trigger FROM filters WHERE chat_id=?", (str(chat_id),))
    return [r[0] for r in cur.fetchall()]

def db_clear_filters(chat_id):
    cur = DB.cursor()
    cur.execute("DELETE FROM filters WHERE chat_id=?", (str(chat_id),))
    DB.commit()

def db_get_replies(chat_id, trigger):
    cur = DB.cursor()
    cur.execute("""
        SELECT reply_type, reply_text, file_id, markup
        FROM filters WHERE chat_id=? AND lower(trigger)=lower(?)
    """, (str(chat_id), trigger))
    return cur.fetchall()

def db_connect(user_id, chat_id):
    cur = DB.cursor()
    cur.execute("INSERT OR REPLACE INTO connections (user_id, chat_id) VALUES (?, ?)", (user_id, chat_id))
    DB.commit()

def db_disconnect(user_id):
    cur = DB.cursor()
    cur.execute("DELETE FROM connections WHERE user_id=?", (user_id,))
    DB.commit()

def db_get_connection(user_id):
    cur = DB.cursor()
    cur.execute("SELECT chat_id FROM connections WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    return result[0] if result else None

# ------------------ UTILS ------------------
def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

def extract_markup(reply_msg):
    markup_data = []
    markup = reply_msg.reply_markup
    if not markup:
        return None
    try:
        if isinstance(markup, dict) and "inline_keyboard" in markup:
            for row in markup["inline_keyboard"]:
                markup_data.append([{"text": b.get("text"), "url": b.get("url")} for b in row])
        elif hasattr(markup, "inline_keyboard"):
            for row in markup.inline_keyboard:
                markup_data.append([{"text": b.text, "url": b.url} for b in row])
    except:
        pass
    return json.dumps(markup_data) if markup_data else None

def rebuild_markup(markup_json):
    if not markup_json:
        return None
    try:
        data = json.loads(markup_json)
        markup = types.InlineKeyboardMarkup()
        for row in data:
            buttons = []
            for b in row:
                buttons.append(types.InlineKeyboardButton(text=b["text"], url=b.get("url")))
            markup.row(*buttons)
        return markup
    except:
        return None

# ------------------ COMMANDS ------------------
@bot.message_handler(commands=['start'])
def start(msg):
    text = (
        "👋 *Welcome to Ultimate Filter Bot!*\n\n"
        "Create auto replies from any message, with or without buttons.\n\n"
        "🧩 *Commands:*\n"
        "`/filter <word>` — Reply to a message to save it\n"
        "`/button <word> <text> <url>` — Reply to sticker/photo to add button\n"
        "`/stop <word>` — Delete a filter\n"
        "`/filters` — List all filters\n"
        "`/stop_all` — Delete all filters\n"
        "`/connect` — Link a group\n"
        "`/disconnect` — Unlink group\n\n"
        "⚙️ Make me *admin* in your group for best results!"
    )
    bot.reply_to(msg, text, parse_mode="Markdown")

@bot.message_handler(commands=['connect'])
def connect(msg):
    if msg.chat.type == "private":
        bot.reply_to(msg, "⚙️ Send this command in the group where I'm added.")
        return
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(msg, "⚠️ Only admins can connect me.")
        return
    db_connect(user_id, chat_id)
    bot.reply_to(msg, "✅ Group connected to your PM!")

@bot.message_handler(commands=['disconnect'])
def disconnect(msg):
    db_disconnect(msg.from_user.id)
    bot.reply_to(msg, "🔌 Disconnected successfully!")

@bot.message_handler(commands=['filter'])
def add_filter(msg):
    user_id = msg.from_user.id
    chat_id = msg.chat.id

    if msg.chat.type == "private":
        conn = db_get_connection(user_id)
        if not conn:
            bot.reply_to(msg, "⚠️ Use /connect in a group first!")
            return
        chat_id = conn
    elif not is_admin(chat_id, user_id):
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

    reply_msg = msg.reply_to_message
    markup = extract_markup(reply_msg)

    if reply_msg.text:
        safe_text = html.escape(reply_msg.text)
        ok = db_add_filter(chat_id, trigger, "text", safe_text, markup=markup)
    elif reply_msg.sticker:
        ok = db_add_filter(chat_id, trigger, "sticker", file_id=reply_msg.sticker.file_id, markup=markup)
    elif reply_msg.photo:
        ok = db_add_filter(chat_id, trigger, "photo", file_id=reply_msg.photo[-1].file_id, markup=markup)
    elif reply_msg.video:
        ok = db_add_filter(chat_id, trigger, "video", file_id=reply_msg.video.file_id, markup=markup)
    else:
        bot.reply_to(msg, "❌ Unsupported message type.")
        return

    if ok:
        bot.reply_to(msg, f"✅ Filter '{trigger}' saved successfully!")
    else:
        bot.reply_to(msg, f"⚠️ Filter '{trigger}' already exists!")

@bot.message_handler(commands=['button'])
def add_button(msg):
    if not msg.reply_to_message:
        bot.reply_to(msg, "📎 Reply to a sticker/photo message with `/button <trigger> <text> <url>`", parse_mode="Markdown")
        return

    parts = msg.text.split()
    if len(parts) < 4:
        bot.reply_to(msg, "❌ Usage:\n`/button <trigger> <button_text> <url>`", parse_mode="Markdown")
        return

    trigger = parts[1].lower()
    button_pairs = parts[2:]

    if len(button_pairs) % 2 != 0:
        bot.reply_to(msg, "⚠️ Button text and URL must be in pairs!", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup()
    for i in range(0, len(button_pairs), 2):
        btn_text = button_pairs[i]
        btn_url = button_pairs[i + 1]
        markup.add(types.InlineKeyboardButton(text=btn_text, url=btn_url))

    reply_msg = msg.reply_to_message

    if reply_msg.sticker:
        db_add_filter(msg.chat.id, trigger, "sticker", file_id=reply_msg.sticker.file_id, markup=json.dumps([[{"text": btn_text, "url": btn_url}] for i in range(0, len(button_pairs), 2)]))
        bot.reply_to(msg, f"✅ Filter '{trigger}' saved with button!")
    elif reply_msg.photo:
        db_add_filter(msg.chat.id, trigger, "photo", file_id=reply_msg.photo[-1].file_id, markup=json.dumps([[{"text": btn_text, "url": btn_url}] for i in range(0, len(button_pairs), 2)]))
        bot.reply_to(msg, f"✅ Filter '{trigger}' saved with button!")
    else:
        bot.reply_to(msg, "⚠️ Only sticker or photo messages supported for button filters.")

@bot.message_handler(commands=['stop'])
def stop_filter(msg):
    chat_id = msg.chat.id
    user_id = msg.from_user.id

    if msg.chat.type == "private":
        conn = db_get_connection(user_id)
        if not conn:
            bot.reply_to(msg, "⚠️ Use /connect first!")
            return
        chat_id = conn
    elif not is_admin(chat_id, user_id):
        bot.reply_to(msg, "⚠️ Only admins can remove filters.")
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: `/stop <word>`", parse_mode="Markdown")
        return
    trigger = parts[1].strip().lower()

    if db_remove_filter(chat_id, trigger):
        bot.reply_to(msg, f"🗑️ Filter '{trigger}' removed.")
    else:
        bot.reply_to(msg, f"⚠️ No filter found for '{trigger}'.")

@bot.message_handler(commands=['filters'])
def list_filters(msg):
    fl = db_list_filters(msg.chat.id)
    if not fl:
        bot.reply_to(msg, "📭 No filters saved.")
    else:
        bot.reply_to(msg, "📋 *Filters:*\n" + "\n".join([f"• {w}" for w in fl]), parse_mode="Markdown")

@bot.message_handler(commands=['stop_all'])
def clear_all(msg):
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    if msg.chat.type != "private" and not is_admin(chat_id, user_id):
        bot.reply_to(msg, "⚠️ Only admins can clear all filters.")
        return
    db_clear_filters(chat_id)
    bot.reply_to(msg, "🧹 All filters cleared.")

# ------------------ MESSAGE HANDLER ------------------
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_trigger(msg):
    chat_id = msg.chat.id
    text = msg.text.lower().strip()
    replies = db_get_replies(chat_id, text)
    if not replies:
        return
    for reply_type, reply_text, file_id, markup_json in replies:
        markup = rebuild_markup(markup_json)
        try:
            if reply_type == "text":
                bot.send_message(chat_id, html.unescape(reply_text), reply_markup=markup)
            elif reply_type == "sticker":
                bot.send_sticker(chat_id, file_id, reply_markup=markup)
            elif reply_type == "photo":
                bot.send_photo(chat_id, file_id, reply_markup=markup)
            elif reply_type == "video":
                bot.send_video(chat_id, file_id, reply_markup=markup)
        except Exception as e:
            print("Error sending:", e)

# ------------------ START ------------------
print("🤖 Ultimate Filter Bot (Unlimited + OG + Buttons + Stickers) starting...")
bot.infinity_polling()

