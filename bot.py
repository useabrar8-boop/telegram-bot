import os
import asyncio
import re
import urllib.request
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

def expand_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.url
    except:
        return url

def get_youtube_id(url):
    match = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None

def get_ydl_base():
    return {
        'quiet': True,
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36',
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

def get_video_title(url):
    if any(x in url for x in ['vt.tiktok.com', 'vm.tiktok.com', 'pin.it', 't.co', 'bit.ly']):
        url = expand_url(url)
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
    if any(x in url for x in ['vt.tiktok.com', 'vm.tiktok.com', 'pin.it', 't.co', 'bit.ly']):
        url = expand_url(url)

    base_opts = get_ydl_base()

    if quality == "audio":
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'restrictfilenames': True,
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'restrictfilenames': True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
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
            "যেকোনো ভিডিও লিংক পাঠান।\n\n"
            "✅ Facebook, TikTok, Instagram, Pinterest সহ ১০০০+ সাইট সাপোর্টেড।"
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

    await show_menu(message, text)

async def show_menu(message, url):
    status_msg = await message.reply_text("⏳ লিংক প্রসেস হচ্ছে...")
    try:
        loop = asyncio.get_event_loop()
        title = await loop.run_in_executor(None, get_video_title, url)
        await status_msg.delete()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 ভিডিও ডাউনলোড", callback_data=f"dl|video|{url}"),
                InlineKeyboardButton("🎵 অডিও ডাউনলোড", callback_data=f"dl|audio|{url}"),
            ]
        ])

        await message.reply_text(
            f"🎬 *{title}*\n\n👇 কী ডাউনলোড করবেন?",
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
            await show_menu(query.message, url)
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

        q_name = "ভিডিও" if quality == "video" else "অডিও"
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
                await query.message.reply_audio(audio=open(file_path, 'rb'), caption="✅ অডিও রেডি! 🎵")
            else:
                await query.message.reply_video(video=open(file_path, 'rb'), caption="✅ ভিডিও রেডি! 🎬")

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
