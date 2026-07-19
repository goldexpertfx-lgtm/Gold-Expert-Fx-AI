import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatJoinRequestHandler, ContextTypes

# 1. Database Setup
def init_db():
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT)''')
    conn.commit()
    conn.close()

# 2. Start with Custom Keyboard
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Edit Post', 'Edit Button']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Gold Expert FX AI Bot active hai:", reply_markup=reply_markup)

# 3. Button Handler
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Edit Post':
        await update.message.reply_text("Post edit karne ke liye text bhejein (Format: /editpost <content>)")
    elif text == 'Edit Button':
        await update.message.reply_text("Button edit karne ke liye link bhejein (Format: /editlink <url>)")
    else:
        # Link Deletion logic agar koi link bheje
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type in ['url', 'text_link']:
                    await update.message.delete()
                    return

# 4. Command Handlers
async def edit_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Post update kar di gayi hai!")

async def edit_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Button link update ho gaya hai!")

# 5. Join Request & Users
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user.id, user.first_name))
    conn.commit()
    conn.close()
    await context.bot.approve_chat_join_request(chat_id=update.chat_join_request.chat.id, user_id=user.id)

if __name__ == '__main__':
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("editpost", edit_post))
    app.add_handler(CommandHandler("editlink", edit_link))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_buttons))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    print("Bot is running...")
    app.run_polling()
    
