import os
import threading
import uuid
import hashlib
import requests
import asyncio
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

app = Flask(__name__)
app.secret_key = "spay_super_secret_key"

# ----------------- CONFIGURATION -----------------
MONGO_URI = "mongodb+srv://wajsarif461_db_user:TwacJh76mwpHHpjpw@cluster0.biueyst.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
TELEGRAM_BOT_TOKEN = "8432557033:AAGts8uHMdhRVaNFTHX3_tp2VYUEZQGEr78"
# -------------------------------------------------

client = MongoClient(MONGO_URI)
db = client["spay_gateway"]
users_collection = db["users"]
orders_collection = db["orders"]

# --- HELPER FUNCTION FOR RENDER ---
def render_page(shop, title, body_content, active_tab=""):
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ title }} - FamPay Gateway</title>
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
            <div class="sidebar-brand"><span>💳</span> FamPay Gateway</div>
            <div style="padding: 15px 20px; font-size: 13px; color: #666; font-weight: 600; border-bottom: 1px solid #eee;">
                Shop: <span style="color:#111;">{{ shop.get('shop_name', 'Merchant') }}</span>
            </div>
            <a href="/dashboard" class="{% if active_tab == 'overview' %}active{% endif %}">📊 Overview</a>
            <a href="/dashboard/apikey" class="{% if active_tab == 'apikey' %}active{% endif %}">🔑 API Key</a>
            <a href="/dashboard/orders" class="{% if active_tab == 'orders' %}active{% endif %}">📦 Recent Orders</a>
            <a href="/dashboard/api-docs" class="{% if active_tab == 'apidocs' %}active{% endif %}">📄 API Docs</a>
            <a href="/dashboard/payment-setup" class="{% if active_tab == 'paymentsetup' %}active{% endif %}">⚙️ Payment Setup</a>
            <a href="/dashboard/payment-link" class="{% if active_tab == 'paymentlink' %}active{% endif %}">🔗 Your Payment Link</a>
            <a href="/dashboard/withdraw" class="{% if active_tab == 'withdraw' %}active{% endif %}">💸 Withdraw & Balance</a>
            <a href="/logout" style="color: #e74c3c; margin-top: 20px;">🚪 Logout</a>
        </div>
        <div class="header">
            <span style="font-weight: 700; color: #333; font-size: 15px;">Merchant Dashboard</span>
            <span style="background: #e1f5fe; color: #0288d1; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700;">Plan: Free</span>
        </div>
        <div class="main-content">
            {{ body_content | safe }}
        </div>
    </body>
    </html>
    """, shop=shop, title=title, body_content=body_content, active_tab=active_tab)

# --- LANDING PAGE ---
@app.route("/")
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FamPay Gateway - Multi-Merchant UPI Payment API</title>
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
            <div class="logo"><span>💳</span> FamPay Gateway</div>
            <div class="nav-btns">
                <a href="/login" class="btn-login">Login</a>
                <a href="/signup" class="btn-getstarted">Get Started</a>
            </div>
        </header>
        <div class="hero">
            <h1>Accept UPI payments, straight to your own account.</h1>
            <p class="desc">Connect your own UPI ID once. Every payment lands directly with you and gets marked "paid" automatically — no manual checking, no middleman holding your money.</p>
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
        try:
            shop_name = request.form.get("shop_name")
            mobile = request.form.get("mobile")
            password = request.form.get("password")
            
            if not shop_name or not mobile or not password:
                return "<script>alert('All fields are required!'); window.location='/signup';</script>"
                
            if users_collection.find_one({"mobile": mobile}):
                return "<script>alert('This mobile number is already registered. Please log in.'); window.location='/signup';</script>"
                
            api_key = "FAM_" + hashlib.sha256(f"{shop_name}_{mobile}_{uuid.uuid4()}".encode()).hexdigest()[:32].upper()
            
            users_collection.insert_one({
                "shop_name": shop_name, "mobile": mobile, "password": password, 
                "upi_id": "", "gmail": "", "gmail_pass": "", "api_key": api_key, "balance": 0.0
            })
            
            session["shop_name"] = shop_name
            return redirect(url_for("dashboard"))
        except Exception as e:
            return f"<script>alert('Error: {str(e)}'); window.location='/signup';</script>"
        
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Register - FamPay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: sans-serif; background: #fdfbf7; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 35px; border-radius: 12px; width: 380px; border: 1px solid #eaeaea; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
            <h2 style="text-align:center; margin-top:0; font-size:16px; color:#555;">CREATE YOUR MERCHANT ACCOUNT</h2>
            <h1 style="text-align:center; font-size:24px; color:#111; margin-bottom:20px;">Register</h1>
            <form method="POST">
                <label style="font-size:13px; font-weight:600; color:#444;">Your Name / Shop Name</label>
                <input type="text" name="shop_name" placeholder="e.g. Rohan Store" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Mobile Number</label>
                <input type="text" name="mobile" placeholder="e.g. 9876543210" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Password</label>
                <input type="password" name="password" placeholder="At least 6 characters" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <button type="submit" style="background: #d35400; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top:10px;">Create Account</button>
            </form>
            <p style="text-align:center; margin-top:15px; font-size:13px;"><a href="/login" style="color:#d35400; text-decoration:none; font-weight:600;">Already have an account? Login here</a></p>
        </div>
    </body>
    </html>
    """)

# --- LOGIN ROUTE ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            login_id = request.form.get("mobile")
            password = request.form.get("password")
            
            user = users_collection.find_one({
                "$or": [{"mobile": login_id}, {"gmail": login_id}],
                "password": password
            })
            
            if user:
                session["shop_name"] = user["shop_name"]
                return redirect(url_for("dashboard"))
            return "<script>alert('Invalid mobile/email or password!'); window.location='/login';</script>"
        except Exception as e:
            return f"<script>alert('Error: {str(e)}'); window.location='/login';</script>"
        
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Login - FamPay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: sans-serif; background: #fdfbf7; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 35px; border-radius: 12px; width: 380px; border: 1px solid #eaeaea; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
            <h2 style="text-align:center; margin-top:0; font-size:16px; color:#555;">MERCHANT LOGIN</h2>
            <form method="POST">
                <label style="font-size:13px; font-weight:600; color:#444;">Mobile Number or Gmail</label>
                <input type="text" name="mobile" placeholder="Enter mobile or gmail" required style="width:100%; padding:10px; margin:6px 0 14px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
                <label style="font-size:13px; font-weight:600; color:#444;">Password</label>
                <input type="password" name="password" required style="width:100%; padding:10px; margin:6px 0 20px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;">
                
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
    if not shop: return redirect(url_for("logout"))
    orders_count = orders_collection.count_documents({"shop_name": shop["shop_name"]})
    
    warning_banner = ""
    if not shop.get('upi_id') or not shop.get('gmail'):
        warning_banner = """
        <div style="background: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 12px 20px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; display:flex; justify-content:space-between; align-items:center;">
            <span>⚠️ Payment Setup is incomplete — please add your UPI ID and Gmail in "Payment Setup".</span>
            <a href="/dashboard/payment-setup" style="color: #856404; font-weight:bold; text-decoration:underline;">Complete it now →</a>
        </div>
        """

    body = f"""
    {warning_banner}
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Overview</h2>
    <div class="grid-stats">
        <div class="stat-card"><div><p>Today's Orders</p><h3>{orders_count}</h3></div></div>
        <div class="stat-card"><div><p>Today's Total</p><h3 style="color:#27ae60;">₹0.00</h3></div></div>
        <div class="stat-card"><div><p>All-Time Orders</p><h3>{orders_count}</h3></div></div>
        <div class="stat-card"><div><p>All-Time Total</p><h3 style="color:#27ae60;">₹{shop.get('balance', 0.0)}</h3></div></div>
    </div>
    """
    return render_page(shop, "Overview", body, "overview")

@app.route("/dashboard/apikey")
def dashboard_apikey():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    if not shop: return redirect(url_for("logout"))
    
    body = f"""
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">API Key</h2>
    <div class="card" style="max-width: 500px; background: linear-gradient(135deg, #2c3e50, #4ca1af); color: white; border-radius: 16px;">
        <p style="margin:0 0 10px 0; font-size:12px; opacity:0.8;">YOUR API KEY</p>
        <h3 id="apikey-text" style="font-family:monospace; font-size:16px; word-break:break-all; margin:0 0 20px 0;">{shop.get('api_key')}</h3>
        <p style="margin:0; font-size:12px; font-weight:bold;">CARD HOLDER: {shop.get('shop_name', '').upper()}</p>
    </div>
    <div style="margin-top:15px;">
        <button onclick="navigator.clipboard.writeText('{shop.get('api_key')}'); alert('API Key Copied!');" class="btn" style="background:#333;">Copy Key</button>
    </div>
    """
    return render_page(shop, "API Key", body, "apikey")

@app.route("/dashboard/orders")
def dashboard_orders():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    if not shop: return redirect(url_for("logout"))
    orders = list(orders_collection.find({"shop_name": shop["shop_name"]}))
    
    rows = ""
    if orders:
        for o in orders:
            rows += f"""<tr style="border-bottom:1px solid #f9f9f9;"><td style="padding:8px;">{o.get('order_id')}</td><td>₹{o.get('amount')}</td><td><span style="color:green;">{o.get('status')}</span></td></tr>"""
        table_html = f"""
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
            <tr style="border-bottom:1px solid #eee; text-align:left;"><th style="padding:8px;">Order ID</th><th>Amount</th><th>Status</th></tr>
            {rows}
        </table>"""
    else:
        table_html = '<p style="color:#666; font-size:14px; margin:0;">No orders yet.</p>'

    body = f"""
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Recent Orders</h2>
    <div class="card">
        {table_html}
    </div>
    """
    return render_page(shop, "Recent Orders", body, "orders")

@app.route("/dashboard/api-docs")
def dashboard_api_docs():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    if not shop: return redirect(url_for("logout"))
    
    host_url = request.host_url
    body = f"""
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">API Docs</h2>
    <div class="card">
        <h3 style="margin-top:0; font-size:15px;">Create an order</h3>
        <pre style="background:#f4f4f4; padding:10px; border-radius:6px; font-size:12px; overflow-x:auto;"><code>GET {host_url}api/create_order.php?amount=99&api_key={shop.get('api_key')}</code></pre>
        
        <h3 style="font-size:15px; margin-top:20px;">Check payment status</h3>
        <pre style="background:#f4f4f4; padding:10px; border-radius:6px; font-size:12px; overflow-x:auto;"><code>GET {host_url}api/check_payment.php?order_id=YOUR_ORDER_ID&api_key={shop.get('api_key')}</code></pre>
    </div>
    """
    return render_page(shop, "API Docs", body, "apidocs")

@app.route("/dashboard/payment-setup", methods=["GET", "POST"])
def dashboard_payment_setup():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    if not shop: return redirect(url_for("logout"))
    
    if request.method == "POST":
        upi_id = request.form.get("upi_id")
        gmail = request.form.get("gmail")
        gmail_pass = request.form.get("gmail_pass")
        users_collection.update_one({"shop_name": shop["shop_name"]}, {"$set": {"upi_id": upi_id, "gmail": gmail, "gmail_pass": gmail_pass}})
        return redirect(url_for("dashboard_payment_setup"))
        
    body = f"""
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Payment Setup</h2>
    <div class="card" style="max-width: 600px;">
        <form method="POST">
            <label style="font-size:13px; font-weight:600; color:#444;">UPI ID (Where you want payments)</label>
            <input type="text" name="upi_id" value="{shop.get('upi_id', '')}" required>
            
            <label style="font-size:13px; font-weight:600; color:#444;">Gmail Address (For Auto-verification)</label>
            <input type="email" name="gmail" value="{shop.get('gmail', '')}" required>
            
            <label style="font-size:13px; font-weight:600; color:#444;">Gmail App Password</label>
            <input type="password" name="gmail_pass" value="{shop.get('gmail_pass', '')}" required>
            
            <button type="submit" class="btn">Save Payment Setup</button>
        </form>
    </div>
    """
    return render_page(shop, "Payment Setup", body, "paymentsetup")

@app.route("/dashboard/payment-link")
def dashboard_payment_link():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    if not shop: return redirect(url_for("logout"))
    
    body = f"""
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Your Payment Link</h2>
    <div class="card">
        <label style="font-size:13px; font-weight:600; color:#555;">Direct Payment URL</label>
        <input type="text" readonly value="{request.host_url}pay?key={shop.get('api_key')}" style="background:#f9f9f9;">
    </div>
    """
    return render_page(shop, "Your Payment Link", body, "paymentlink")

@app.route("/dashboard/withdraw")
def dashboard_withdraw():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    if not shop: return redirect(url_for("logout"))
    
    body = f"""
    <h2 style="margin-top:0; font-size: 22px; font-weight: 800;">Withdraw & Balance</h2>
    <div class="card">
        <p style="margin:0 0 10px 0; font-size:14px; color:#555;">Available Balance: <strong style="color:#27ae60; font-size:18px;">₹{shop.get('balance', 0.0)}</strong></p>
    </div>
    """
    return render_page(shop, "Withdraw & Balance", body, "withdraw")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- PAYMENT PAGE ---
@app.route("/pay")
def pay_page():
    order_id = request.args.get("order_id")
    key = request.args.get("key")
    
    order = None
    shop = None
    
    if order_id:
        order = orders_collection.find_one({"order_id": order_id})
        if order:
            shop = users_collection.find_one({"shop_name": order["shop_name"]})
    elif key:
        shop = users_collection.find_one({"api_key": key})
        
    if not shop:
        return "<h1>Invalid Payment Link or Shop Not Found</h1>", 404
        
    amount = order["amount"] if order else "10.00"
    o_id = order_id if order else "DIRECT_PAY"
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pay to {{ shop.shop_name }}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: sans-serif; background: #fdfbf7; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .pay-box { background: white; padding: 30px; border-radius: 12px; width: 350px; text-align: center; border: 1px solid #eaeaea; box-shadow: 0 4px 15px rgba(0,0,0,0.02); }
            h2 { margin-top: 0; color: #111; }
            .amount { font-size: 28px; font-weight: bold; color: #27ae60; margin: 15px 0; }
            .btn { background: #d35400; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; text-decoration: none; display: inline-block; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="pay-box">
            <h2>{{ shop.shop_name }}</h2>
            <p style="color: #666; font-size: 13px; margin:0;">Order ID: {{ o_id }}</p>
            <div class="amount">₹{{ amount }}</div>
            <p style="font-size: 13px; color: #444;">Pay using any UPI app to:</p>
            <p style="font-family: monospace; font-weight: bold; background: #f4f4f4; padding: 8px; border-radius: 6px;">{{ shop.get('upi_id', 'Not Set') }}</p>
            <a href="upi://pay?pa={{ shop.get('upi_id') }}&pn={{ shop.shop_name }}&am={{ amount }}&cu=INR" class="btn">Pay Now via UPI App</a>
        </div>
    </body>
    </html>
    """, shop=shop, amount=amount, o_id=o_id)

# --- API ENDPOINTS ---
@app.route("/api/create_order.php")
def api_create_order():
    api_key = request.args.get("api_key")
    amount = request.args.get("amount")
    shop = users_collection.find_one({"api_key": api_key})
    if not shop:
        return jsonify({"status": "error", "message": "Invalid API Key"})
    
    order_id = "FAM_" + hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:12].upper()
    orders_collection.insert_one({
        "shop_name": shop["shop_name"], "order_id": order_id, "amount": amount, "status": "PENDING"
    })
    
    return jsonify({
        "status": "success",
        "result": {
            "order_id": order_id,
            "amount": amount,
            "payment_url": f"{request.host_url}pay?order_id={order_id}"
        }
    })

@app.route("/api/check_payment.php")
def api_check_payment():
    api_key = request.args.get("api_key")
    order_id = request.args.get("order_id")
    shop = users_collection.find_one({"api_key": api_key})
    if not shop:
        return jsonify({"status": "error", "message": "Invalid API Key"})
    
    order = orders_collection.find_one({"order_id": order_id, "shop_name": shop["shop_name"]})
    if not order:
        return jsonify({"status": "error", "message": "Order not found"})
        
    return jsonify({
        "status": "success",
        "data": {
            "order_id": order_id,
            "amount": order["amount"],
            "payment_status": order["status"]
        }
    })

# --- TELEGRAM BOT LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🌐 Visit Web Panel", url="https://github.com/SPY-BOTZ")]]
    await update.message.reply_text("✨ Welcome to FamPay Gateway Bot!", reply_markup=InlineKeyboardMarkup(keyboard))

def run_telegram_bot():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def main():
            # Thoda wait karein taaki purana instance puri tarah disconnect ho jaye
            await asyncio.sleep(3)
            app_bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
            app_bot.add_handler(CommandHandler("start", start))
            await app_bot.initialize()
            await app_bot.start()
            # drop_pending_updates=True se purane conflicts ignore ho jayenge
            await app_bot.updater.start_polling(drop_pending_updates=True)
            await asyncio.Event().wait()
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Telegram Bot Notice: {e}")

if __name__ == "__main__":
    t = threading.Thread(target=run_telegram_bot)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
