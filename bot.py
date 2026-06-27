import os
import asyncio
import re
import urllib.request
import urllib.parse
import json
from datetime import datetime
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler

BOT_TOKEN = "8495929411:AAHQRXgkItKjf_ZUZyEKogTsUsWJfqiWoQg"
CHANNEL_USERNAME = "@maimuna3600"
CHANNEL_LINK = "https://t.me/maimuna3600"
OWNER_ID = 5483673756
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

os.makedirs("downloads", exist_ok=True)

def get_youtube_id(url):
    match = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None

def get_ydl_base():
    return {
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
        },
    }

def get_video_title_api(video_id):
    try:
        api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_API_KEY}&part=snippet"
        req = urllib.request.Request(api_url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            items = data.get('items', [])
            if items:
                return items[0]['snippet']['title']
    except:
        pass
    return None

def get_stream_url(video_id, quality):
    try:
        base_opts = get_ydl_base()
        if quality == "audio":
            fmt = 'bestaudio/best'
        else:
            height_map = {"1080": 1080, "720": 720, "480": 480, "360": 360}
            h = height_map.get(quality, 720)
            fmt = f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}]/best'

        ydl_opts = {
            **base_opts,
            'format': fmt,
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'merge_output_format': 'mp4',
        }
        if quality == "audio":
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url=f"https://www.youtube.com/watch?v={video_id}", download=True)
            path = ydl.prepare_filename(info)
            if quality == "audio":
                path = os.path.splitext(path)[0] + ".mp3"
            elif not path.endswith('.mp4'):
                mp4 = os.path.splitext(path)[0] + ".mp4"
                if os.path.exists(mp4):
                    path = mp4
            return path
    except Exception as e:
        raise e

def get_video_title(url):
    video_id = get_youtube_id(url)
    if video_id and YOUTUBE_API_KEY:
        title = get_video_title_api(video_id)
        if title:
            return title
    ydl_opts = get_ydl_base()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get('title', 'ভিডিও')

def download_video(url, quality):
    video_id = get_youtube_id(url)
    if video_id:
        return get_stream_url(video_id, quality)

    base_opts = get_ydl_base()
    if quality == "audio":
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        height_map = {"1080": 1080, "720": 720, "480": 480, "360": 360}
        height = height_map.get(quality, 720)
        ydl_opts = {
            **base_opts,
            'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'merge_output_format': 'mp4',
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        if quality == "audio":
            path = os.path.splitext(path)[0] + ".mp3"
        elif not path.endswith('.mp4'):
            mp4 = os.path.splitext(path)[0] + ".mp4"
            if os.path.exists(mp4):
                path = mp4
        return path

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def notify_owner(bot, user, url, quality):
    try:
        username = f"@{user.username}" if user.username else "নেই"
        time_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        text = (
            f"📥 নতুন ডাউনলোড!\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 নাম: {user.first_name}\n"
            f"🆔 ID: {user.id}\n"
            f"📛 Username: {username}\n"
            f"🎯 কোয়ালিটি: {quality}\n"
            f"🔗 লিংক: {url}\n"
            f"🕐 সময়: {time_now}"
        )
        await bot.send_message(chat_id=OWNER_ID, text=text)
    except:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    text = message.text.strip()

    if not re.match(r'^(http|https)://', text):
        await message.reply_text(
            "👋 স্বাগতম!\n\n"
            "যেকোনো ভিডিও লিংক পাঠান এবং পছন্দের কোয়ালিটি বেছে নিন।\n\n"
            "✅ YouTube, Facebook, TikTok, Instagram সহ ১০০০+ সাইট সাপোর্টেড।"
        )
        return

    subscribed = await is_subscribed(context.bot, user_id)
    if not subscribed:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ চ্যানেলে জয়েন করুন", url=CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 জয়েন করেছি, চেক করুন", callback_data=f"check|{text}")]
        ])
        await message.reply_text(
            "❌ বটটি ব্যবহার করতে আগে আমাদের চ্যানেলে জয়েন করুন!\n\n"
            f"👇 জয়েন করুন: {CHANNEL_LINK}\n\n"
            "জয়েন করার পর নিচের 🔄 বাটনে ক্লিক করুন।",
            reply_markup=keyboard
        )
        return

    await show_quality_menu(message, text)

async def show_quality_menu(message, url):
    status_msg = await message.reply_text("⏳ ভিডিও তথ্য সংগ্রহ করা হচ্ছে...")
    try:
        loop = asyncio.get_event_loop()
        title = await loop.run_in_executor(None, get_video_title, url)
        await status_msg.delete()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔥 1080p", callback_data=f"dl|1080|{url}"),
                InlineKeyboardButton("📺 720p", callback_data=f"dl|720|{url}"),
            ],
            [
                InlineKeyboardButton("📱 480p", callback_data=f"dl|480|{url}"),
                InlineKeyboardButton("🎞 360p", callback_data=f"dl|360|{url}"),
            ],
            [
                InlineKeyboardButton("🎵 শুধু অডিও (MP3)", callback_data=f"dl|audio|{url}"),
            ]
        ])

        await message.reply_text(
            f"🎬 *{title}*\n\n"
            "👇 কোন কোয়ালিটিতে ডাউনলোড করবেন বেছে নিন:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ লিংক প্রসেস করা যায়নি:\n{str(e)}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    data = query.data

    if data.startswith("check|"):
        url = data.split("|", 1)[1]
        subscribed = await is_subscribed(context.bot, user_id)
        if subscribed:
            await query.answer("✅ যাচাই সফল!")
            await query.message.delete()
            await show_quality_menu(query.message, url)
        else:
            await query.answer("❌ আপনি এখনো জয়েন করেননি!", show_alert=True)
        return

    if data.startswith("dl|"):
        parts = data.split("|", 2)
        quality = parts[1]
        url = parts[2]

        subscribed = await is_subscribed(context.bot, user_id)
        if not subscribed:
            await query.answer("❌ আগে চ্যানেলে জয়েন করুন!", show_alert=True)
            return

        quality_names = {"1080": "1080p HD", "720": "720p", "480": "480p", "360": "360p", "audio": "MP3 Audio"}
        q_name = quality_names.get(quality, quality)

        await query.answer(f"⬇️ {q_name} ডাউনলোড শুরু হচ্ছে...")
        await query.message.edit_text(f"📥 {q_name} ডাউনলোড হচ্ছে... অনুগ্রহ করে অপেক্ষা করুন।")

        await notify_owner(context.bot, user, url, q_name)

        try:
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, download_video, url, quality)

            if not file_path or not os.path.exists(file_path):
                raise Exception("ফাইল ডাউনলোড হয়নি।")

            await query.message.edit_text("📤 আপলোড হচ্ছে...")

            if quality == "audio":
                await query.message.reply_audio(audio=open(file_path, 'rb'), caption="✅ আপনার অডিও রেডি! 🎵")
            else:
                await query.message.reply_video(video=open(file_path, 'rb'), caption=f"✅ {q_name} ভিডিও রেডি! 🎬")

            if os.path.exists(file_path):
                os.remove(file_path)
            await query.message.delete()

        except Exception as e:
            await query.message.edit_text(f"❌ সমস্যা হয়েছে:\n{str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).read_timeout(300).write_timeout(300).connect_timeout(300).pool_timeout(300).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("🤖 বট চালু হয়েছে!")
    app.run_polling()

if __name__ == "__main__":
    main()
