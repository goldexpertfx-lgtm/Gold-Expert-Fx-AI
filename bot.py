import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ChatJoinRequestHandler, CallbackQueryHandler

# Database Setup
def init_db():
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT)''')
    conn.commit()
    conn.close()

# 1. Link Deletion (Community Management)
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.entities:
        for entity in update.message.entities:
            if entity.type in ['url', 'text_link']:
                await update.message.delete()
                return

# 2. Join Request Approval
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user.id, user.first_name))
    conn.commit()
    conn.close()
    await context.bot.approve_chat_join_request(chat_id=update.chat_join_request.chat.id, user_id=user.id)

# 3. User Tracking & Admin Reply
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('gold_expert_fx.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    msg = "👥 **Total Users List:**\n" + "\n".join([f"ID: {u[0]} | Name: {u[1]}" for u in users])
    await update.message.reply_text(msg)

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) >= 2:
        await context.bot.send_message(chat_id=context.args[0], text=f"📩 Admin: {' '.join(context.args[1:])}")

# 4. Post & Button Management
async def edit_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Aap yahan se apna custom message update kar sakte hain
    await update.message.reply_text("Post updated successfully!")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), filter_links))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(CommandHandler("edit", edit_post))
    
    app.run_polling()
    
