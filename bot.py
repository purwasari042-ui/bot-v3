from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# 10 Tingkat Gelar Kekalahan
GELAR_LIST = {
    0: "Aman",
    1: "RT (Rukun Tetangga)",
    2: "RW (Rukun Warga)",
    3: "Lurah",
    4: "Camat",
    5: "Walikota / Bupati",
    6: "Gubernur",
    7: "Menteri",
    8: "Wakil Presiden",
    9: "Presiden",
    10: "Tolol 👑"
}

games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🃏 *Bot Remi RT/RW (Menu Interaktif)* 🃏\n\n"
        "📌 *Perintah Utama:*\n"
        "• `/pemain A B C` atau `/pemain A B C D` : Daftarkan 3 hingga 4 pemain\n"
        "• `/input` : Buka menu tombol pemilihan pemain & skor\n"
        "• `/skor` : Lihat papan skor saat ini\n"
        "• `/status` : Lihat riwayat gelar RT s/d Sultan",
        parse_mode="Markdown"
    )

async def set_pemain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nama_pemain = context.args
    
    # Validasi jumlah pemain: Minimal 3, Maksimal 4
    if not (3 <= len(nama_pemain) <= 4):
        await update.message.reply_text(
            "❌ Jumlah pemain harus *3 atau 4 orang*!\n"
            "Contoh 3 pemain: `/pemain Budi Andi Siti`\n"
            "Contoh 4 pemain: `/pemain Budi Andi Siti Dewi`",
            parse_mode="Markdown"
        )
        return
    
    if chat_id not in games:
        games[chat_id] = {
            "players": {},
            "history_kalah": {},
            "active_player": None,
            "draft_poin": 0,
            "is_negative": False
        }
    
    games[chat_id]["players"] = {p: 0 for p in nama_pemain}
    for p in nama_pemain:
        if p not in games[chat_id]["history_kalah"]:
            games[chat_id]["history_kalah"][p] = 0
            
    await update.message.reply_text(f"✅ Game dimulai! Pemain ({len(nama_pemain)} orang): *{', '.join(nama_pemain)}*\nKetik `/input` untuk mulai memasukkan poin.", parse_mode="Markdown")

async def open_input_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id]["players"]:
        await update.message.reply_text("Daftarkan pemain dulu dengan `/pemain A B C` (atau 4 orang)!")
        return
    
    players = games[chat_id]["players"]
    buttons = [[InlineKeyboardButton(f"👤 {p}", callback_data=f"select_{p}")] for p in players.keys()]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎯 *Pilih pemain yang ingin diinput poinnya:*", reply_markup=keyboard, parse_mode="Markdown")

def build_score_keyboard(draft_poin, is_negative):
    mode_text = "➖ Mode: NEGATIF (-)" if is_negative else "➕ Mode: POSITIF (+)"
    toggle_callback = "toggle_mode_pos" if is_negative else "toggle_mode_neg"
    
    keyboard = [
        [InlineKeyboardButton(mode_text, callback_data=toggle_callback)],
        [
            InlineKeyboardButton("5", callback_data="val_5"),
            InlineKeyboardButton("10", callback_data="val_10"),
            InlineKeyboardButton("20", callback_data="val_20")
        ],
        [
            InlineKeyboardButton("30", callback_data="val_30"),
            InlineKeyboardButton("40", callback_data="val_40"),
            InlineKeyboardButton("50", callback_data="val_50")
        ],
        [
            InlineKeyboardButton("100", callback_data="val_100"),
            InlineKeyboardButton("🔄 Reset", callback_data="reset_draft")
        ],
        [InlineKeyboardButton(f"✅ KONFIRMASI ({draft_poin:+d} Poin)", callback_data="confirm_score")],
        [InlineKeyboardButton("🔙 Kembali ke Pilih Pemain", callback_data="back_to_players")]
    ]
    return InlineKeyboardMarkup(keyboard)

def check_overtake_and_reset(old_scores, new_scores):
    resets = []
    messages = []
    for p_a, score_a in new_scores.items():
        if 100 <= score_a <= 499:
            for p_b, score_b in new_scores.items():
                if p_a != p_b:
                    if old_scores[p_b] <= old_scores[p_a] and score_b > score_a:
                        resets.append(p_a)
                        messages.append(f"🔥 *{p_b}* menyalip *{p_a}*! Poin {p_a} *RESET KE 0*!")
                        break
    for p in set(resets):
        new_scores[p] = 0
    return new_scores, messages

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    data = query.data
    game = games.get(chat_id)
    if not game:
        await query.edit_message_text("Game tidak ditemukan. Ketik `/pemain` untuk memulai.")
        return
    
    if data.startswith("select_"):
        player_name = data.split("_")[1]
        game["active_player"] = player_name
        game["draft_poin"] = 0
        game["is_negative"] = False
        
        teks = f"👤 Pemain Terpilih: *{player_name}*\nAkumulasi Input: *{game['draft_poin']}*\n\nSilakan pilih tombol angka di bawah:"
        keyboard = build_score_keyboard(game["draft_poin"], game["is_negative"])
        await query.edit_message_text(teks, parse_mode="Markdown", reply_markup=keyboard)
        
    elif data == "back_to_players":
        players = game["players"]
        buttons = [[InlineKeyboardButton(f"👤 {p}", callback_data=f"select_{p}")] for p in players.keys()]
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("🎯 *Pilih pemain yang ingin diinput poinnya:*", reply_markup=keyboard, parse_mode="Markdown")
        
    elif data in ["toggle_mode_pos", "toggle_mode_neg"]:
        game["is_negative"] = (data == "toggle_mode_neg")
        player_name = game["active_player"]
        
        teks = f"👤 Pemain Terpilih: *{player_name}*\nAkumulasi Input: *{game['draft_poin']}*\n\nSilakan pilih tombol angka di bawah:"
        keyboard = build_score_keyboard(game["draft_poin"], game["is_negative"])
        await query.edit_message_text(teks, parse_mode="Markdown", reply_markup=keyboard)
            
    elif data.startswith("val_") or data == "reset_draft":
        if data == "reset_draft":
            game["draft_poin"] = 0
        else:
            val = int(data.split("_")[1])
            if game["is_negative"]:
                game["draft_poin"] -= val
            else:
                game["draft_poin"] += val
                
        player_name = game["active_player"]
        keyboard = build_score_keyboard(game["draft_poin"], game["is_negative"])
        
        try:
            await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
                
    elif data == "confirm_score":
        player_name = game["active_player"]
        draft = game["draft_poin"]
        if draft == 0:
            await query.answer("Poin masih 0, pilih angka terlebih dahulu!", show_alert=True)
            return
        
        old_scores = game["players"].copy()
        game["players"][player_name] += draft
        game["players"], notif_salip = check_overtake_and_reset(old_scores, game["players"])
        
        pesan_notif = f"✅ Poin *{player_name}* berhasil ditambah ({draft:+d} poin)."
        if notif_salip:
            pesan_notif += "\n" + "\n".join(notif_salip)
            
        await process_game_result(update, context, chat_id, pesan_notif)

async def process_game_result(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, notifikasi: str):
    query = update.callback_query
    game = games[chat_id]
    players = game["players"]
    history = game["history_kalah"]
    
    kalah_instan = [p for p, score in players.items() if score <= -500]
    pemenang = [p for p, score in players.items() if score >= 500]
    
    game_over = False
    pecundang = None
    pesan_akhir = ""
    
    if kalah_instan:
        game_over = True
        pecundang = kalah_instan[0]
        history[pecundang] += 1
        pesan_akhir = f"💀 *GAME OVER!*\n*{pecundang}* menyentuh poin <= -500 ({players[pecundang]}) dan *LANGSUNG KALAH*!"
    elif pemenang:
        game_over = True
        juara = max(players, key=players.get)
        pecundang = min(players, key=players.get)
        history[pecundang] += 1
        pesan_akhir = f"🎉 *GAME OVER!*\n🏆 Pemenang Putaran: *{juara}* ({players[juara]} poin)\n💔 Kalah Putaran Ini: *{pecundang}* ({players[pecundang]} poin)"
        
    papan = "📊 *PAPAN SKOR SAAT INI* 📊\n" + "\n".join([f"• {p}: *{s}* poin" for p, s in players.items()])
    teks_tampil = f"{notifikasi}\n\n{papan}"
    
    if game_over:
        k_count = history[pecundang]
        gelar = GELAR_LIST.get(k_count, GELAR_LIST[10])
        pesan_akhir += f"\n\n🏛️ Status {pecundang} sekarang: *{gelar}* (Total akumulasi kalah: {k_count}x)"
        
        games[chat_id]["players"] = {p: 0 for p in players.keys()}
        
        buttons = [[InlineKeyboardButton(f"👤 {p}", callback_data=f"select_{p}")] for p in players.keys()]
        keyboard = InlineKeyboardMarkup(buttons)
        
        await query.message.delete()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{teks_tampil}\n\n{pesan_akhir}\n\n🔄 *Ronde Baru Dimulai! Pilih pemain untuk input poin:*",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        buttons = [[InlineKeyboardButton(f"👤 {p}", callback_data=f"select_{p}")] for p in players.keys()]
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(f"{teks_tampil}\n\n🎯 *Pilih pemain berikutnya untuk diinput poinnya:*", parse_mode="Markdown", reply_markup=keyboard)

async def skor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id]["players"]:
        await update.message.reply_text("Belum ada skor aktif. Ketik `/pemain` untuk memulai.", parse_mode="Markdown")
        return
    players = games[chat_id]["players"]
    papan = "📊 *PAPAN SKOR SAAT INI* 📊\n" + "\n".join([f"• {p}: *{s}* poin" for p, s in players.items()])
    await update.message.reply_text(papan, parse_mode="Markdown")

async def status_rtrw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("Belum ada data permainan.")
        return
    history = games[chat_id]["history_kalah"]
    teks = "🏛️ *STATUS GELAR DAN JABATAN PEMAIN* (Hingga 10 Tingkat) 🏛️\n\n"
    for p, count in history.items():
        gelar = GELAR_LIST.get(count, GELAR_LIST[10])
        teks += f"• {p}: *{gelar}* (Total kalah: {count}x)\n"
    await update.message.reply_text(teks, parse_mode="Markdown")

import os
from flask import Flask

# ... (simpan semua kode fungsi bot Anda di atas bagian ini seperti biasa) ...

# Konfigurasi Flask untuk Uptime 24 Jam di Cloud
server = Flask(__name__)

@server.route("/")
def index():
    return "Bot Remi RT/RW Aktif 24 Jam!", 200

if __name__ == '__main__':
    TOKEN = "8854147147:AAFZ-NokjXUlvzPDhxaw4myHVBLpXPfS210"
    PORT = int(os.environ.get("PORT", 5000))
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pemain", set_pemain))
    app.add_handler(CommandHandler("input", open_input_menu))
    app.add_handler(CommandHandler("skor", skor))
    app.add_handler(CommandHandler("status", status_rtrw))
    app.add_handler(CallbackQueryHandler(button_click_handler))
    
    # Jalankan bot dengan polling secara bersamaan dengan web server
    print("Bot Remi Interaktif & Web Server Berjalan...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://bot-v3-j7bq.onrender.com/{TOKEN}" # Ganti nanti setelah deploy di Render
    )
