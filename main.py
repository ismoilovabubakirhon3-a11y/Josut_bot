import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler
)
from database import init_db, add_player, update_stats, get_top_players

# Loggingni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

games = {}

WORDS = [
    "To'yxona", "Choyxona", "Universitet", "Bozor", "Samolyot", 
    "Metropoliten", "Restoran", "Kasalxona", "Supermarket", "Stadion",
    "Mahalla", "Sartaroshxona", "Aqvapark", "Kinozal", "Maktab"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ **'Kim o'sha josus?'** o'yin botiga xush kelibsiz!\n\n"
        "Guruhda o'yinni boshlash uchun:\n"
        "👉 `/play` - O'yinni boshlash\n"
        "👉 `/join` - O'yinga qo'shilish\n"
        "👉 `/top` - Reytingni ko'rish"
    )

async def top_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = get_top_players()
    if not top:
        await update.message.reply_text("🏆 Hozircha reyting bo'sh. O'yin o'ynang!")
        return
    
    text = "🏆 **Eng yaxshi o'yinchilar reytingi:**\n\n"
    for idx, (uname, wins, played) in enumerate(top, 1):
        name = uname or "Noma'lum"
        text += f"{idx}. {name} — 🥇 G'alaba: {wins} ta (O'yinlar: {played})\n"
    
    await update.message.reply_text(text)

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id in games and games[chat_id]['active']:
        await update.message.reply_text("⚠️ Bu guruhda allaqachon o'yin ketmoqda!")
        return

    games[chat_id] = {
        'players': {},
        'spy': None,
        'word': None,
        'active': True,
        'phase': 'joining'
    }
    
    msg = await update.message.reply_text(
        "🎮 **Yangi josus o'yini ochildi!**\n\n"
        "Qatnashmoqchi bo'lganlar **6 daqiqa** ichida `/join` buyrug'ini bosing!\n"
        "Hozirgi qatnashchilar: 0 ta"
    )
    
    # 360 soniya (har 20 soniyada xabarni yangilab turadi)
    for i in range(18):
        await asyncio.sleep(20)
        if chat_id not in games or not games[chat_id]['active']:
            return
        count = len(games[chat_id]['players'])
        left_time = 360 - ((i + 1) * 20)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.message_id,
                text=f"🎮 **Yangi josus o'yini ochildi!**\n\n"
                     f"Qatnashish uchun `/join` buyrug'ini bosing!\n"
                     f"Qatnashchilar soni: **{count}** ta\n"
                     f"⏳ Qolgan vaqt: **{left_time} soniya**"
            )
        except Exception:
            pass

    if chat_id not in games:
        return
        
    players = games[chat_id]['players']
    if len(players) < 3:
        games[chat_id]['active'] = False
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ O'yin boshlash uchun kamida **3 ta o'yinchi** kerak edi! O'yin bekor qilindi."
        )
        return

    player_ids = list(players.keys())
    spy_id = random.choice(player_ids)
    secret_word = random.choice(WORDS)

    games[chat_id]['spy'] = spy_id
    games[chat_id]['word'] = secret_word
    games[chat_id]['phase'] = 'playing'

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🚀 **O'yin boshlandi!** Ishtirokchilar: {len(players)} kishi.\n\n"
             f"🤫 Hammaga rollar va maxfiy so'zlar **shaxsiy xabarga (lichkaga)** yuborildi!\n"
             f"Navbatma-navbat bittadan gap gapiring va josusni aniqlang!"
    )

    for p_id in player_ids:
        try:
            if p_id == spy_id:
                await context.bot.send_message(
                    chat_id=p_id,
                    text="🤫 Siz — **JOSUS**siz! Sizga maxfiy so'z berilmadi. Boshqalarni eshitib, so'zni topishga harakat qiling!"
                )
            else:
                await context.bot.send_message(
                    chat_id=p_id,
                    text=f"🔑 Maxfiy so'z: **{secret_word}**\nSiz tinch aholisiz. Josusni aniqlang!"
                )
        except Exception:
            pass

    await asyncio.sleep(15)
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🗳 Josusga ovoz berishni boshlash", callback_data="start_vote")]])
    await context.bot.send_message(
        chat_id=chat_id,
        text="🗣 Muhokama vaqti tugayapti! Kim josus ekanligini aniqladingizmi?",
        reply_markup=keyboard
    )

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id not in games or not games[chat_id]['active'] or games[chat_id]['phase'] != 'joining':
        await update.message.reply_text("Hozir o'yinga qo'shilish vaqti emas yoki o'yin ochilmagan.")
        return
        
    players = games[chat_id]['players']
    if user.id not in players:
        players[user.id] = user.first_name
        add_player(user.id, user.first_name)
        await update.message.reply_text(f"✅ {user.first_name} o'yinga qo'shildi!")
    else:
        await update.message.reply_text(f"@{user.username or user.first_name}, siz allaqachon qo'shilgansiz!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    data = query.data
    
    if data == "start_vote":
        if chat_id not in games or not games[chat_id]['active']:
            return
            
        players = games[chat_id]['players']
        keyboard = []
        for p_id, p_name in players.items():
            keyboard.append([InlineKeyboardButton(p_name, callback_data=f"vote_{p_id}")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "🗳 **OVOZ BERISH BOSHLANDI!**\n\n"
            "Kim josus deb o'ylaysiz? Pastdagi ismlardan birini tanlang:",
            reply_markup=reply_markup
        )
        games[chat_id]['votes'] = {}

    elif data.startswith("vote_"):
        voter_id = query.from_user.id
        suspect_id = int(data.split("_")[1])
        
        if chat_id not in games or not games[chat_id]['active']:
            await query.edit_message_text("O'yin allaqachon tugagan.")
            return
            
        players = games[chat_id]['players']
        if voter_id not in players:
            await query.answer("Siz bu o'yinda qatnashmayapsiz!", show_alert=True)
            return
            
        games[chat_id]['votes'][voter_id] = suspect_id
        await query.answer("Ovozingiz qabul qilindi!")
        
        if len(games[chat_id]['votes']) == len(players):
            votes = games[chat_id]['votes']
            vote_counts = {}
            for s_id in votes.values():
                vote_counts[s_id] = vote_counts.get(s_id, 0) + 1
                
            most_voted = max(vote_counts, key=vote_counts.get)
            spy_id = games[chat_id]['spy']
            secret_word = games[chat_id]['word']
            
            spy_name = players.get(spy_id, "Noma'lum")
            voted_name = players.get(most_voted, "Noma'lum")
            
            for p_id in players.keys():
                won = False
                if most_voted == spy_id:
                    if p_id != spy_id: won = True
                else:
                    if p_id == spy_id: won = True
                update_stats(p_id, won=won)

            result_text = f"🏁 **O'YIN TUGADI! Natijalar:**\n\n"
            result_text += f"🤫 Haqiqiy josus: **{spy_name}** edi!\n"
            result_text += f"🔑 Maxfiy so'z: **{secret_word}**\n"
            result_text += f"👥 Guruh tanlovi: **{voted_name}**\n\n"
            
            if most_voted == spy_id:
                result_text += "🎉 **Tinch aholi g'alaba qozondi!**"
            else:
                result_text += "😈 **Josus g'alaba qozondi!**"
                
            await query.message.edit_text(result_text)
            games[chat_id]['active'] = False

def main():
    init_db()
    TOKEN = "9119312680:AAFJh7AfyBsQ5GOpSKVF1uV9zRBK_JKz5gs"
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top_players))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("join", join_game))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()

if __name__ == '__main__':
    main()
