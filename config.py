import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

# Chat where screenshots + conversation get forwarded (can be a group with
# several admins in it, or just your own DM with the bot).
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Only THIS Telegram user ID's replies/button-taps are relayed to customers.
# Everyone else in ADMIN_CHAT_ID can only watch.
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gefx_orders.db")

# ---------------------------------------------------------------------------
# Products, prices, and VIP invite links.
# Edit these to match your real pricing / channel links.
# ---------------------------------------------------------------------------
PRODUCTS = {
    "vip_monthly":        {"label": "VIP Monthly Membership",   "price": "49 USDT",  "invite_link": "https://t.me/+your_monthly_invite"},
    "vip_quarterly":      {"label": "VIP Quarterly Membership", "price": "129 USDT", "invite_link": "https://t.me/+your_quarterly_invite"},
    "vip_half_year":      {"label": "VIP Half Year Membership", "price": "229 USDT", "invite_link": "https://t.me/+your_halfyear_invite"},
    "vip_yearly":         {"label": "VIP Yearly Membership",    "price": "399 USDT", "invite_link": "https://t.me/+your_yearly_invite"},
    "vip_lifetime":       {"label": "VIP Lifetime Membership",  "price": "699 USDT", "invite_link": "https://t.me/+your_lifetime_invite"},
    "copy_trading":       {"label": "Copy Trading",             "price": "Contact for pricing", "invite_link": "https://t.me/+your_copytrading_invite"},
    "account_management": {"label": "Account Management",       "price": "Contact for pricing", "invite_link": "https://t.me/+your_accountmgmt_invite"},
}

# Payment methods shown to the customer. Edit addresses/details to your real ones.
PAYMENT_METHODS = {
    "binance_pay":   {"label": "Binance Pay",   "details": "Binance Pay ID: XXXXXXXX"},
    "usdt_trc20":    {"label": "USDT (TRC20)",  "details": "Address: T-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "usdt_bep20":    {"label": "USDT (BEP20)",  "details": "Address: 0xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "btc":           {"label": "Bitcoin",       "details": "Address: bc1xxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "eth":           {"label": "Ethereum",      "details": "Address: 0xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "ltc":           {"label": "Litecoin",      "details": "Address: Lxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "perfect_money": {"label": "Perfect Money", "details": "Account: Uxxxxxxx"},
    "skrill":        {"label": "Skrill",        "details": "Email: payments@goldexpertfx.com"},
    "neteller":      {"label": "Neteller",      "details": "Email: payments@goldexpertfx.com"},
    "payoneer":      {"label": "Payoneer",      "details": "Email: payments@goldexpertfx.com"},
    "wise":          {"label": "Wise",          "details": "Email: payments@goldexpertfx.com"},
    "bank_transfer": {"label": "Bank Transfer",  "details": "Contact admin for bank details"},
}
