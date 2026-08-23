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
TELEGRAM_BOT_TOKEN = "8432557033:AAH97OnOUBklHDGYbIpY63RPKd6vThujF0I"
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
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; margin: 0; padding: 0; color: #333; }
        .sidebar { width: 250px; background: #fff; position: fixed; height: 100%; border-right: 1px solid #dee2e6; padding-top: 20px; }
        .sidebar a { padding: 12px 20px; display: block; color: #333; text-decoration: none; font-size: 15px; font-weight: 500; border-left: 3px solid transparent; }
        .sidebar a:hover, .sidebar a.active { background: #f1f3f5; border-left-color: #d35400; color: #d35400; }
        .main-content { margin-left: 250px; padding: 30px; }
        .header { background: #fff; padding: 15px 30px; border-bottom: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center; margin-left: 250px; }
        .card { background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { background: #fff; padding: 20px; border-radius: 10px; border: 1px solid #eaeaea; }
        input, select { width: 100%; padding: 10px; margin: 8px 0 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        @media(max-width: 768px) { .sidebar { width: 100%; height: auto; position: relative; } .main-content, .header { margin-left: 0; } }
    </style>
</head>
<body>
    <div class="sidebar">
        <div style="padding: 0 20px; font-size: 20px; font-weight: bold; color: #d35400; margin-bottom: 20px;">💳 S-Pay Gateway</div>
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

# --- PROFESSIONAL LANDING PAGE (FAM-PAY STYLE) ---
@app.route("/")
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>S-Pay Gateway - Multi-Merchant UPI Payment API</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #fdfbf7; margin: 0; padding: 0; color: #222; }
            header { display: flex; justify-content: space-between; align-items: center; padding: 20px 8%; border-bottom: 1px solid #eee; background: #fff; position: sticky; top: 0; z-index: 100; }
            .logo { font-weight: bold; font-size: 20px; color: #111; display: flex; align-items: center; gap: 8px; }
            .logo span { background: #d35400; color: white; padding: 4px 8px; border-radius: 4px; }
            .nav-btns a { margin-left: 15px; text-decoration: none; font-weight: 600; font-size: 14px; }
            .btn-login { color: #333; padding: 8px 16px; }
            .btn-getstarted { background: #d35400; color: white; padding: 8px 16px; border-radius: 6px; }
            
            .hero { text-align: center; padding: 80px 20px 40px 20px; max-width: 800px; margin: 0 auto; }
            .subtitle { font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: #888; font-weight: 700; margin-bottom: 15px; }
            h1 { font-size: 42px; line-height: 1.2; font-weight: 800; color: #111; margin-bottom: 20px; }
            p.desc { font-size: 16px; color: #555; line-height: 1.6; margin-bottom: 30px; }
            
            .badges { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 40px; }
            .badge { background: #fff; border: 1px solid #e5e5e5; padding: 6px 14px; border-radius: 20px; font-size: 13px; color: #444; font-weight: 500; }
            
            .cta-group { margin-bottom: 60px; }
            .btn-main { background: #d35400; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 15px; display: inline-block; margin-right: 10px; }
            .btn-sec { background: #fff; color: #333; border: 1px solid #ccc; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 15px; display: inline-block; }
            
            .section-title { text-align: center; font-size: 24px; font-weight: 800; margin-bottom: 10px; }
            .section-sub { text-align: center; color: #666; font-size: 14px; margin-bottom: 40px; }
            
            .steps-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; padding: 0 8% 80px 8%; max-width: 1100px; margin: 0 auto; }
            .step-card { background: #fff; border: 1px solid #eaeaea; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
            .step-num { font-size: 13px; font-weight: bold; color: #d35400; background: #fae5d3; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-bottom: 15px; }
            .step-card h3 { font-size: 18px; margin-bottom: 10px; color: #111; }
            .step-card p { font-size: 14px; color: #666; line-height: 1.5; }
            
            .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; padding: 0 8% 80px 8%; max-width: 1100px; margin: 0 auto; }
            .feature-box { background: #fff; border: 1px solid #eaeaea; padding: 20px; border-radius: 10px; font-size: 14px; font-weight: 600; color: #333; display: flex; align-items: center; gap: 12px; }
            
            .footer-banner { background: #fff; border: 1px solid #eaeaea; border-radius: 16px; margin: 0 8% 80px 8%; padding: 50px 20px; text-align: center; max-width: 1000px; margin-left: auto; margin-right: auto; }
            footer { text-align: center; padding: 20px; font-size: 12px; color: #777; border-top: 1px solid #eee; background: #fff; }
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
            <div class="subtitle">MULTI-MERCHANT UPI PAYMENT API</div>
            <h1>Accept UPI payments, straight to your own account.</h1>
            <p class="desc">Connect your own UPI ID once. Every payment lands directly with you and gets marked "paid" automatically — no manual checking, no middleman holding your money.</p>
            
            <div class="badges">
                <div class="badge">✔️ Direct to your UPI ID</div>
                <div class="badge">✔️ Automatic verification</div>
                <div class="badge">✔️ No KYC, no signup fee</div>
            </div>
            
            <div class="cta-group">
                <a href="/signup" class="btn-main">Create free account</a>
                <a href="/login" class="btn-sec">Login</a>
            </div>
        </div>

        <div class="section-title">How it works</div>
        <div class="section-sub">Three steps — set up once, runs on its own after that.</div>
        
        <div class="steps-container">
            <div class="step-card">
                <div class="step-num">01</div>
                <h3>Generate a QR</h3>
                <p>Call one API endpoint with an amount, get back a UPI QR code for your customer to scan.</p>
            </div>
            <div class="step-card">
                <div class="step-num">02</div>
                <h3>Customer pays you directly</h3>
                <p>Any UPI app works — GPay, PhonePe, Paytm, BHIM. Money reaches your own UPI ID instantly.</p>
            </div>
            <div class="step-card">
                <div class="step-num">03</div>
                <h3>Order confirmed automatically</h3>
                <p>Within moments the order flips to "paid" on its own — you never have to manually confirm a payment.</p>
            </div>
        </div>

        <div class="section-title">Why merchants trust this</div>
        <div class="section-sub">Built so you're always the one in control of your own money.</div>

        <div class="features-grid">
            <div class="feature-box">🛡️ Money never passes through us</div>
            <div class="feature-box">⚡ Isolated per merchant</div>
            <div class="feature-box">🔒 Full control, anytime</div>
            <div class="feature-box">⏳ Orders auto-expire</div>
        </div>

        <div class="footer-banner">
            <h2>Your API key and full docs live in your dashboard</h2>
            <p style="color: #666; font-size: 14px; margin-bottom: 25px;">Register free, add your UPI ID, and every endpoint — with your real key already filled in — is one click away.</p>
            <a href="/signup" class="btn-main">Create free account</a>
            <a href="/login" class="btn-sec">I already have an account</a>
        </div>

        <footer>
            Self-hosted • direct-to-merchant UPI collection • no subscription, no middleman.
        </footer>
    </body>
    </html>
    """)

# --- SIGNUP PAGE ROUTE ---
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
    <body style="font-family: Arial; background: #fdfbf7; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 35px; border-radius: 12px; width: 380px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eaeaea;">
            <h2 style="margin-top:0; color:#111;">Create Free Account</h2>
            <form method="POST">
                <label style="font-size:13px; font-weight:600; color:#444;">Shop Name</label>
                <input type="text" name="shop_name" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Email / Phone</label>
                <input type="text" name="email" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Your UPI ID (For Withdrawal)</label>
                <input type="text" name="upi_id" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Telegram ID (Optional for Bot Sync)</label>
                <input type="text" name="tg_id" style="width:100%; padding:10px; margin:6px 0 20px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <button type="submit" style="background: #d35400; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 15px;">Register</button>
            </form>
            <p style="text-align:center; margin-top:15px; font-size:13px;"><a href="/login" style="color:#d35400; text-decoration:none; font-weight:600;">Already have an account? Login</a></p>
        </div>
    </body>
    </html>
    """)

# --- LOGIN PAGE ROUTE ---
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
    <body style="font-family: Arial; background: #fdfbf7; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 35px; border-radius: 12px; width: 380px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eaeaea;">
            <h2 style="margin-top:0; color:#111;">Welcome Back</h2>
            <form method="POST">
                <label style="font-size:13px; font-weight:600; color:#444;">Shop / Username</label>
                <input type="text" name="shop_name" required style="width:100%; padding:10px; margin:6px 0 20px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <button type="submit" style="background: #d35400; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 15px;">Login</button>
            </form>
            <p style="text-align:center; margin-top:15px; font-size:13px;"><a href="/signup" style="color:#d35400; text-decoration:none; font-weight:600;">Create New Account</a></p>
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
