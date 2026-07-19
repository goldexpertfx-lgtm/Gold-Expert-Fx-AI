import sqlite3
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatJoinRequestHandler, ContextTypes

# 1. Database Setup
def init_db():
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT)''')
    conn.commit()
    conn.close()

# 2. Start Command - Jo bot ko active karega
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Assalam-o-Alaikum! Gold Expert FX AI Bot active hai. 🚀")

# 3. Link Deletion
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.entities:
        for entity in update.message.entities:
            if entity.type in ['url', 'text_link']:
                await update.message.delete()
                return

# 4. Join Request Approval
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user.id, user.first_name))
    conn.commit()
    conn.close()
    await context.bot.approve_chat_join_request(chat_id=update.chat_join_request.chat.id, user_id=user.id)

# 5. User List
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    msg = "👥 **Total Users List:**\n" + "\n".join([f"ID: {u[0]} | Name: {u[1]}" for u in users])
    await update.message.reply_text(msg)

# 6. Admin Reply
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) >= 2:
        await context.bot.send_message(chat_id=context.args[0], text=f"📩 Admin: {' '.join(context.args[1:])}")

# Bot Start Main
if __name__ == '__main__':
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN") # Render mein Environment variable set rakhein
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), filter_links))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    print("Bot is running...")
    app.run_polling()
    
