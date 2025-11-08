import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import InputAudioStream
from pytgcalls.types.input_stream.input_stream import InputStream
from youtube_search import YoutubeSearch
import yt_dlp
import os

API_ID = 23715627  # ← apna API_ID yaha daalo
API_HASH = "26c335fe953856eb72845e02c6c44930"  # ← apna API_HASH
BOT_TOKEN = "8266210982:AAHuYW6CnOz4NasUhW40ta_B-cGIWJAsiMo"  # ← BotFather se mila hua token

app = Client("music-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call = PyTgCalls(app)

# Folder for temp files
os.makedirs("downloads", exist_ok=True)

@call.on_stream_end()
async def on_end(_, update):
    chat_id = update.chat_id
    await call.leave_group_call(chat_id)
    print(f"Playback finished in {chat_id}")

@app.on_message(filters.command("start") & filters.private)
async def start(_, msg):
    await msg.reply_text("🎵 Voice Chat Music Bot is Online!\nUse `/play <song name>` in a group voice chat.")

@app.on_message(filters.command("play") & filters.group)
async def play(_, message):
    if len(message.command) < 2:
        return await message.reply("❌ Please provide a song name.")

    query = " ".join(message.command[1:])
    results = YoutubeSearch(query, max_results=1).to_dict()
    if not results:
        return await message.reply("⚠️ No results found.")
    
    url = f"https://youtube.com{results[0]['url_suffix']}"
    title = results[0]["title"]
    await message.reply(f"🎶 Playing: **{title}**")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "quiet": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
    }

    loop = asyncio.get_event_loop()
    file_path = None
    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return os.path.join("downloads", f"{info['id']}.mp3")

    file_path = await loop.run_in_executor(None, download)
    chat_id = message.chat.id

    await call.join_group_call(
        chat_id,
        InputStream(
            InputAudioStream(
                file_path,
            ),
        ),
    )

    await message.reply(f"▶️ **Now playing:** {title}")

@app.on_message(filters.command("stop") & filters.group)
async def stop(_, message):
    chat_id = message.chat.id
    await call.leave_group_call(chat_id)
    await message.reply("⏹️ Music stopped.")

async def main():
    await app.start()
    await call.start()
    print("✅ Music Bot is running...")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
