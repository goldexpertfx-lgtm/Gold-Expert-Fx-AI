# --- User Menu Keyboard (Jo sabko dikhega) ---
def get_user_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Account Management", callback_data="svc_acc")],
        [InlineKeyboardButton("💎 VIP Services", callback_data="svc_vip")],
        [InlineKeyboardButton("📈 Copy Trading", callback_data="svc_copy")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Admin Keyboard (Jo sirf aapko dikhega) ---
def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("👥 Users List"), KeyboardButton("✏️ Edit Start Text")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# ===== UPDATED START FUNCTION =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_registry[user.id] = user 

    welcome_text = (
        f"**Welcome to Gold Expert Fx Community, {user.first_name}!** 🥇\n\n"
        "Hum aapki trading journey ko professional banane ke liye yahan hain. "
        "Neeche diye gaye buttons se hamari services select karein:"
    )

    if user.id == ADMIN_ID:
        # Admin ko dono dikhenge
        await update.message.reply_text("Admin Control Panel Active:", reply_markup=get_admin_keyboard())
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_user_menu())
    else:
        # Users ko sirf services dikhengi
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_user_menu())

# ===== NEW CALLBACK HANDLER (Services ke liye) =====
async def service_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "svc_acc":
        await query.edit_message_text("🛠 **Account Management:**\nHum aapke account ko expert levels par manage karte hain. Details ke liye contact karein: @MuhammadPrince7")
    elif query.data == "svc_vip":
        await query.edit_message_text("💎 **VIP Services:**\nExclusive signals aur daily market analysis ke liye hamara VIP group join karein.")
    elif query.data == "svc_copy":
        await query.edit_message_text("📈 **Copy Trading:**\nHamare trades ko auto-copy karein. Join link: https://www.brokeraccountguide.com/")
    
