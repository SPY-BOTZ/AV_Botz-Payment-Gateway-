import os
import threading
import uuid
import hashlib
import requests
import asyncio
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

app = Flask(__name__)
app.secret_key = "spay_super_secret_key"

# ----------------- CONFIGURATION -----------------
MONGO_URI = "mongodb+srv://wajsarif461_db_user:TwacJh76mwpHHpjpw@cluster0.biueyst.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
TELEGRAM_BOT_TOKEN = "8432557033:AAGts8uHMdhRVaNFTHX3_tp2VYUEZQGEr78"
LOG_CHANNEL_ID = "-1002580860502" 
ADMIN_UPI_ID = "BHARATPE.9Q0Q0K0Z8Q466572@unitype" 
ADMIN_COMMISSION = 1.0
WEB_URL = "https://usual-catshark-moveshub-450ea334.koyeb.app/"
# -------------------------------------------------

client = MongoClient(MONGO_URI)
db = client["spay_gateway"]
users_collection = db["users"]
orders_collection = db["orders"]
withdrawals_collection = db["withdrawals"]

# --- DASHBOARD LAYOUT TEMPLATE ---
DASHBOARD_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>S-Pay Gateway Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fdfbf7; margin: 0; padding: 0; color: #222; }
        .sidebar { width: 260px; background: #fff; position: fixed; height: 100%; border-right: 1px solid #eaeaea; padding-top: 20px; box-sizing: border-box; overflow-y: auto; }
        .sidebar-brand { padding: 0 20px 20px 20px; font-size: 18px; font-weight: 800; color: #111; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #eee; }
        .sidebar-brand span { background: #d35400; color: white; padding: 3px 6px; border-radius: 4px; font-size: 14px; }
        .sidebar a { padding: 12px 20px; display: block; color: #444; text-decoration: none; font-size: 14px; font-weight: 600; border-left: 3px solid transparent; }
        .sidebar a:hover, .sidebar a.active { background: #f9f9f9; border-left-color: #d35400; color: #d35400; }
        .main-content { margin-left: 260px; padding: 35px; box-sizing: border-box; }
        .header { background: #fff; padding: 15px 35px; border-bottom: 1px solid #eaeaea; display: flex; justify-content: space-between; align-items: center; margin-left: 260px; position: sticky; top: 0; z-index: 10; }
        .card { background: #fff; padding: 25px; border-radius: 12px; border: 1px solid #eaeaea; box-shadow: 0 2px 8px rgba(0,0,0,0.01); margin-bottom: 20px; }
        .grid-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .stat-card { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #eaeaea; display: flex; justify-content: space-between; align-items: center; }
        .stat-card div p { margin: 0 0 5px 0; font-size: 12px; color: #777; font-weight: 600; text-transform: uppercase; }
        .stat-card div h3 { margin: 0; font-size: 20px; color: #111; font-weight: 700; }
        input, select { width: 100%; padding: 12px; margin: 8px 0 16px 0; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
        .btn { background: #d35400; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }
        @media(max-width: 768px) { .sidebar { width: 100%; height: auto; position: relative; } .main-content, .header { margin-left: 0; } }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-brand"><span>💳</span> S-Pay Gateway</div>
        <div style="padding: 15px 20px; font-size: 13px; color: #666; font-weight: 600; border-bottom: 1px solid #eee;">
            Shop: <span style="color:#111;">{{ shop.shop_name }}</span>
        </div>
        <a href="/dashboard" class="{% if request.path == '/dashboard' %}active{% endif %}">📊 Overview</a>
        <a href="/dashboard/apikey" class="{% if request.path == '/dashboard/apikey' %}active{% endif %}">🔑 API Key</a>
        <a href="/dashboard/orders" class="{% if request.path == '/dashboard/orders' %}active{% endif %}">📦 Recent Orders</a>
        <a href="/dashboard/payment-setup" class="{% if request.path == '/dashboard/payment-setup' %}active{% endif %}">⚙️ Payment Setup</a>
        <a href="/dashboard/payment-link" class="{% if request.path == '/dashboard/payment-link' %}active{% endif %}">🔗 Your Payment Link</a>
        <a href="/dashboard/withdraw" class="{% if request.path == '/dashboard/withdraw' %}active{% endif %}">💸 Withdraw & Balance</a>
        <a href="/logout" style="color: #e74c3c; margin-top: 20px;">🚪 Logout</a>
    </div>
    <div class="header">
        <span style="font-weight: 700; color: #333; font-size: 15px;">Merchant Dashboard</span>
        <span style="background: #e1f5fe; color: #0288d1; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700;">Plan: Free</span>
    </div>
    <div class="main-content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# --- PROFESSIONAL LANDING PAGE ---
@app.route("/")
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>S-Pay Gateway - Multi-Merchant UPI Payment API</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fdfbf7; margin: 0; padding: 0; color: #222; }
            header { display: flex; justify-content: space-between; align-items: center; padding: 20px 8%; border-bottom: 1px solid #eee; background: #fff; position: sticky; top: 0; z-index: 100; }
            .logo { font-weight: bold; font-size: 20px; color: #111; display: flex; align-items: center; gap: 8px; }
            .logo span { background: #d35400; color: white; padding: 4px 8px; border-radius: 4px; }
            .nav-btns a { margin-left: 15px; text-decoration: none; font-weight: 600; font-size: 14px; }
            .btn-login { color: #333; padding: 8px 16px; }
            .btn-getstarted { background: #d35400; color: white; padding: 8px 16px; border-radius: 6px; }
            .hero { text-align: center; padding: 80px 20px 40px 20px; max-width: 800px; margin: 0 auto; }
            h1 { font-size: 42px; line-height: 1.2; font-weight: 800; color: #111; margin-bottom: 20px; }
            p.desc { font-size: 16px; color: #555; line-height: 1.6; margin-bottom: 30px; }
            .btn-main { background: #d35400; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 15px; display: inline-block; margin-right: 10px; }
            .btn-sec { background: #fff; color: #333; border: 1px solid #ccc; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 15px; display: inline-block; }
        </style>
    </head>
    <body>
        <header>
            <div class="logo"><span>💳</span> S-Pay Gateway</div>
            <div class="nav-btns">
                <a href="/login" class="btn-login">Login</a>
                <a href="/signup" class="btn-getstarted">Get Started</a>
            </div>
        </header>
        <div class="hero">
            <h1>Accept UPI payments, straight to your own account.</h1>
            <p class="desc">Connect your own UPI ID once. Every payment lands directly with you and gets marked "paid" automatically.</p>
            <div>
                <a href="/signup" class="btn-main">Create free account</a>
                <a href="/login" class="btn-sec">Login</a>
            </div>
        </div>
    </body>
    </html>
    """)

# --- SIGNUP ROUTE ---
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        email = request.form.get("email")
        upi_id = request.form.get("upi_id")
        tg_id = request.form.get("tg_id", "")
        
        if users_collection.find_one({"shop_name": shop_name}):
            return "<script>alert('Shop name already taken!'); window.location='/signup';</script>"
            
        api_key = "SPAY_" + hashlib.sha256(f"{shop_name}_{email}_{uuid.uuid4()}".encode()).hexdigest()[:32].upper()
        
        users_collection.insert_one({
            "shop_name": shop_name, "email": email, "upi_id": upi_id, "telegram_id": tg_id, "api_key": api_key, "balance": 0.0
        })
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                "chat_id": LOG_CHANNEL_ID,
                "text": f"<b>🚀 New Web Registration!</b>\n🏪 Shop: {shop_name}\n📧 Email/Phone: {email}\n💳 UPI: <code>{upi_id}</code>\n🤖 Telegram ID: {tg_id}\n🔑 Key: <code>{api_key}</code>",
                "parse_mode": "HTML"
            })
        except Exception as e:
            print("Telegram Error:", e)
        
        session["shop_name"] = shop_name
        return redirect(url_for("dashboard"))
        
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Signup - S-Pay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: sans-serif; background: #fdfbf7; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 35px; border-radius: 12px; width: 380px; border: 1px solid #eaeaea; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
            <h2 style="margin-top:0; color:#111;">Create Free Account</h2>
            <form method="POST">
                <label style="font-size:13px; font-weight:600; color:#444;">Shop Name</label>
                <input type="text" name="shop_name" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Email / Phone</label>
                <input type="text" name="email" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Your UPI ID (For Withdrawal)</label>
                <input type="text" name="upi_id" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Telegram ID (Optional)</label>
                <input type="text" name="tg_id" style="width:100%; padding:10px; margin:6px 0 20px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <button type="submit" style="background: #d35400; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer;">Register</button>
            </form>
            <p style="text-align:center; margin-top:15px; font-size:13px;"><a href="/login" style="color:#d35400; text-decoration:none; font-weight:600;">Already have an account? Login</a></p>
        </div>
    </body>
    </html>
    """)

# --- LOGIN ROUTE ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        if users_collection.find_one({"shop_name": shop_name}):
            session["shop_name"] = shop_name
            return redirect(url_for("dashboard"))
        return "<script>alert('Shop not found!'); window.location='/login';</script>"
        
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Login - S-Pay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: sans-serif; background: #fdfbf7; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 35px; border-radius: 12px; width: 380px; border: 1px solid #eaeaea; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
            <h2 style="margin-top:0; color:#111;">Welcome Back</h2>
            <form method="POST">
                <label style="font-size:13px; font-weight:600; color:#444;">Shop / Username</label>
                <input type="text" name="shop_name" required style="width:100%; padding:10px; margin:6px 0 20px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <button type="submit" style="background: #d35400; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer;">Login</button>
            </form>
            <p style="text-align:center; margin-top:15px; font-size:13px;"><a href="/signup" style="color:#d35400; text-decoration:none; font-weight:600;">Create New Account</a></p>
        </div>
    </body>
    </html>
    """)

# --- DASHBOARD PAGES ---
@app.route("/dashboard")
def dashboard():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Today's Snapshot</h2>
    <div class="grid-stats">
        <div class="stat-card"><div><p>Today's Orders</p><h3>0</h3></div></div>
        <div class="stat-card"><div><p>Today's Total</p><h3 style="color:#27ae60;">₹0.00</h3></div></div>
        <div class="stat-card"><div><p>All-Time Orders</p><h3>0</h3></div></div>
        <div class="stat-card"><div><p>All-Time Total</p><h3 style="color:#27ae60;">₹0.00</h3></div></div>
    </div>
    <div class="card">
        <h3 style="margin-top:0; font-size:16px;">How to Use</h3>
        <p style="font-size:13px; color:#666;">Connect your UPI ID and use the API key to integrate seamless payments into your applications.</p>
    </div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/apikey")
def dashboard_apikey():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">API Key Management</h2>
    <div class="card">
        <label style="font-size:13px; font-weight:600; color:#555;">Your Secret API Key</label>
        <input type="text" readonly value="{{ shop.api_key }}" style="background:#f9f9f9; font-family:monospace;">
    </div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/orders")
def dashboard_orders():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    orders = list(orders_collection.find({"shop_name": shop["shop_name"]}))
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Recent Orders</h2>
    <div class="card">
        {% if orders %}
            <p>Orders found.</p>
        {% else %}
            <p style="color:#666; font-size:14px; margin:0;">No orders found yet.</p>
        {% endif %}
    </div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/payment-setup")
def dashboard_payment_setup():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Payment Setup</h2>
    <div class="card">
        <label style="font-size:13px; font-weight:600; color:#555;">Connected UPI ID</label>
        <input type="text" readonly value="{{ shop.upi_id }}" style="background:#f9f9f9;">
    </div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/payment-link")
def dashboard_payment_link():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Your Payment Link</h2>
    <div class="card">
        <label style="font-size:13px; font-weight:600; color:#555;">Direct Payment URL</label>
        <input type="text" readonly value="{{ request.host_url }}pay?key={{ shop.api_key }}" style="background:#f9f9f9;">
    </div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/withdraw")
def dashboard_withdraw():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Withdraw & Balance</h2>
    <div class="card">
        <p style="margin:0 0 10px 0; font-size:14px; color:#555;">Available Balance: <strong style="color:#27ae60; font-size:18px;">₹{{ shop.balance }}</strong></p>
    </div>
    {% endblock %}
    """, shop=shop)

@app.route("/logout")
def logout():
    session.pop("shop_name", None)
    return redirect(url_for("home"))

# --- TELEGRAM BOT LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    shop = users_collection.find_one({"telegram_id": tg_id})
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance"), InlineKeyboardButton("👤 My Profile", callback_data="profile")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🌐 Visit Web Panel", url=WEB_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"✨ **HELLO {update.effective_user.first_name}**\n\nWELCOME TO S-PAY GATEWAY BOT..."
    if shop:
        text += f"\n\n✅ Connected Shop: *{shop['shop_name']}*"
    else:
        text += f"\n\n⚠️ *No account linked with Telegram ID ({tg_id})*."
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    shop = users_collection.find_one({"telegram_id": tg_id})
    if query.data == "balance":
        bal = shop["balance"] if shop else 0.0
        await query.message.edit_text(f"💳 **YOUR WALLET BALANCE**\n\nAvailable Balance: ₹{bal}", parse_mode="Markdown")
    elif query.data == "profile":
        if shop:
            await query.message.edit_text(f"👤 **MERCHANT PROFILE**\n\nName: {shop['shop_name']}\nEmail: {shop['email']}\nUPI: {shop['upi_id']}", parse_mode="Markdown")
        else:
            await query.message.edit_text("❌ No account found linked to your Telegram.")
    elif query.data == "withdraw":
        bal = shop["balance"] if shop else 0.0
        await query.message.edit_text(f"💸 **WITHDRAWAL MENU**\n\nAvailable Balance: ₹{bal}", parse_mode="Markdown")

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def main():
        app_bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CallbackQueryHandler(button_handler))
        await app_bot.initialize()
        await app_bot.start()
        await app_bot.updater.start_polling(drop_pending_updates=True)
        stop_event = asyncio.Event()
        await stop_event.wait()
    loop.run_until_complete(main())

if __name__ == "__main__":
    t = threading.Thread(target=run_telegram_bot)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=5000)
