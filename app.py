import os
import threading
import uuid
import hashlib
import requests
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

# --- WEBSITE HTML TEMPLATE ---
DASHBOARD_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>S-Pay Gateway Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; margin: 0; padding: 0; color: #333; }
        .sidebar { width: 250px; background: #fff; position: fixed; height: 100%; border-right: 1px solid #dee2e6; padding-top: 20px; }
        .sidebar a { padding: 12px 20px; display: block; color: #333; text-decoration: none; font-size: 15px; font-weight: 500; border-left: 3px solid transparent; }
        .sidebar a:hover, .sidebar a.active { background: #f1f3f5; border-left-color: #f39c12; color: #f39c12; }
        .main-content { margin-left: 250px; padding: 30px; }
        .header { background: #fff; padding: 15px 30px; border-bottom: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center; margin-left: 250px; }
        .card { background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .btn { background: #f39c12; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { background: #fff; padding: 20px; border-radius: 10px; border: 1px solid #eaeaea; }
        input, select { width: 100%; padding: 10px; margin: 8px 0 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        @media(max-width: 768px) { .sidebar { width: 100%; height: auto; position: relative; } .main-content, .header { margin-left: 0; } }
    </style>
</head>
<body>
    <div class="sidebar">
        <div style="padding: 0 20px; font-size: 20px; font-weight: bold; color: #f39c12; margin-bottom: 20px;">💳 S-Pay Gateway</div>
        <a href="/dashboard">📊 Overview</a>
        <a href="/dashboard/apikey">🔑 API Key</a>
        <a href="/dashboard/orders">📦 Recent Orders</a>
        <a href="/dashboard/docs">📄 API Docs</a>
        <a href="/dashboard/withdraw">💸 Withdraw & Balance</a>
        <a href="/logout" style="color: red; margin-top: 30px;">🚪 Logout</a>
    </div>
    <div class="header">
        <span style="font-weight: bold; color: #555;">Shop: {{ shop.shop_name }}</span>
        <span style="background: #e1f5fe; color: #0288d1; padding: 5px 12px; border-radius: 20px; font-size: 13px;">Plan: Free</span>
    </div>
    <div class="main-content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head><title>S-Pay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <h1>Accept UPI payments, straight to your own account.</h1>
        <br><a href="/signup" style="background: #f39c12; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold;">Create Free Account</a>
        <a href="/login" style="background: #fff; color: #333; border: 1px solid #ccc; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-left: 10px;">Login</a>
    </body>
    </html>
    """)

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
        
        # Telegram Channel par notification bhejne ka code
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
    <html>
    <head><title>Signup - S-Pay</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; background: #f8f9fa; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 30px; border-radius: 12px; width: 350px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2>Create Free Account</h2>
            <form method="POST">
                <label>Shop Name</label><input type="text" name="shop_name" required>
                <label>Email / Phone</label><input type="text" name="email" required>
                <label>Your UPI ID (For Withdrawal)</label><input type="text" name="upi_id" required>
                <label>Telegram ID (Optional for Bot Sync)</label><input type="text" name="tg_id">
                <button type="submit" style="background: #f39c12; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer;">Register</button>
            </form>
            <p style="text-align:center; margin-top:15px;"><a href="/login">Already have an account? Login</a></p>
        </div>
    </body>
    </html>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        if users_collection.find_one({"shop_name": shop_name}):
            session["shop_name"] = shop_name
            return redirect(url_for("dashboard"))
        return "<script>alert('Shop not found!'); window.location='/login';</script>"
        
    return render_template_string("""
    <html>
    <head><title>Login - S-Pay</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; background: #f8f9fa; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 30px; border-radius: 12px; width: 350px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2>Welcome Back</h2>
            <form method="POST">
                <label>Shop / Username</label><input type="text" name="shop_name" required>
                <button type="submit" style="background: #f39c12; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer;">Login</button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route("/dashboard")
def dashboard():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>Overview</h2>
    <div class="grid">
        <div class="stat-box"><p>Wallet Balance</p><h3 style="color:green;">₹{{ shop.balance }}</h3></div>
    </div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/apikey")
def dashboard_apikey():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>API Key</h2>
    <div class="card"><input type="text" readonly value="{{ shop.api_key }}" style="background:#eee;"></div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/orders")
def dashboard_orders():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    orders = list(orders_collection.find({"shop_name": shop["shop_name"]}))
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>Recent Orders</h2>
    <div class="card">{% if orders %}Found{% else %}No orders{% endif %}</div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/docs")
def dashboard_docs():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>API Docs</h2>
    <div class="card"><code>{{ request.host_url }}api/create_order.php?amount=99&api_key={{ shop.api_key }}</code></div>
    {% endblock %}
    """, shop=shop)

@app.route("/dashboard/withdraw")
def dashboard_withdraw():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>Withdraw & Balance</h2>
    <div class="card"><p>Balance: ₹{{ shop.balance }}</p></div>
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
        [InlineKeyboardButton("📦 Transactions", callback_data="transactions"), InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🌐 Visit Web Panel", url=WEB_URL)],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"✨ **HELLO {update.effective_user.first_name}**\n\nWELCOME TO S-PAY GETAWAY BOT..."
    if shop:
        text += f"\n\n✅ Connected Shop: *{shop['shop_name']}*"
    else:
        text += f"\n\n⚠️ *No account linked with Telegram ID ({tg_id})*. Please register on web panel and add your Telegram ID."

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
        await query.message.edit_text(f"💸 **WITHDRAWAL MENU**\n\nAvailable Balance: ₹{bal}\n\nTo withdraw, visit web panel.", parse_mode="Markdown")
    elif query.data == "help":
        await query.message.edit_text("ℹ️ For support contact admin.", parse_mode="Markdown")
    elif query.data == "about":
        await query.message.edit_text("🤖 S-Pay Gateway v1.0 powered by Python & Flask.", parse_mode="Markdown")

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app_bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button_handler))
    app_bot.run_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_telegram_bot)
    t.daemon = True
    t.start()
    
    app.run(host="0.0.0.0", port=5000)
