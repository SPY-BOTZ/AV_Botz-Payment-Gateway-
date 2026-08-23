from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from pymongo import MongoClient
import uuid
import hashlib
import requests

app = Flask(__name__)
app.secret_key = "fampay_super_secret_key" # Session maintain karne ke liye

# ----------------- CONFIGURATION -----------------
MONGO_URI = "mongodb+srv://wajsarif461_db_user:TwacJh76mwpHHpjw@cluster0.biueyst.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
TELEGRAM_BOT_TOKEN = "8432557033:AAGts8uHMdhRVaNFTHX3_tp2VYUEZQGEr78"
LOG_CHANNEL_ID = "-1002580860502" 
ADMIN_SECRET_KEY = "admin123"
# -------------------------------------------------

client = MongoClient(MONGO_URI)
db = client["fampay_gateway"]
users_collection = db["users"]
orders_collection = db["orders"]
withdrawals_collection = db["withdrawals"]

# Common CSS & Sidebar Layout template
LAYOUT_CSS = """
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; margin: 0; padding: 0; color: #333; }
    .header { background: #fff; padding: 15px 30px; border-bottom: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center; }
    .logo { font-weight: bold; font-size: 18px; color: #f39c12; text-decoration: none; display: flex; align-items: center; gap: 8px;}
    .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
    .card { background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .btn { background: #f39c12; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; }
    .btn:hover { background: #d68910; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; }
    .stat-box { background: #fff; padding: 20px; border-radius: 10px; border: 1px solid #eaeaea; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
    input, select { width: 100%; padding: 10px; margin: 8px 0 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
</style>
"""

# 1. Landing Page
@app.route("/")
def home():
    return render_template_string(LAYOUT_CSS + """
    <div class="header">
        <a href="/" class="logo">💳 FamPay Gateway</a>
        <div>
            <a href="/login" class="btn" style="background: transparent; color: #333; border: 1px solid #ccc;">Login</a>
            <a href="/signup" class="btn">Get Started</a>
        </div>
    </div>
    <div class="container" style="text-align: center; padding-top: 50px;">
        <h1 style="font-size: 36px; color: #111;">Accept UPI payments, straight to your own account.</h1>
        <p style="color: #666; font-size: 18px;">Connect your own UPI ID once. Automatic verification, no manual checking, no middleman holding your money.</p>
        <br>
        <a href="/signup" class="btn" style="font-size: 16px; padding: 12px 30px;">Create Free Account</a>
    </div>
    """)

# 2. Signup Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        phone = request.form.get("phone")
        upi_id = request.form.get("upi_id")
        
        if users_collection.find_one({"shop_name": shop_name}):
            return "<script>alert('Shop name already exists!'); window.location='/signup';</script>"
            
        raw_key = f"{shop_name}_{phone}_{uuid.uuid4()}"
        api_key = "FAM_" + hashlib.sha256(raw_key.encode()).hexdigest()[:32].upper()
        
        users_collection.insert_one({
            "shop_name": shop_name,
            "phone": phone,
            "upi_id": upi_id,
            "api_key": api_key,
            "balance": 0.0
        })
        
        # Telegram notification
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                "chat_id": LOG_CHANNEL_ID,
                "text": f"<b>🚨 New Gateway Registration!</b>\n\n🏪 Shop: {shop_name}\n📧 Contact: {phone}\n💳 UPI: <code>{upi_id}</code>\n🔑 API Key: <code>{api_key}</code>",
                "parse_mode": "HTML"
            })
        except:
            pass
            
        session["shop_name"] = shop_name
        return redirect(url_for("dashboard"))
        
    return render_template_string(LAYOUT_CSS + """
    <div class="header"><a href="/" class="logo">💳 FamPay Gateway</a></div>
    <div class="container" style="max-width: 400px;">
        <div class="card">
            <h2>Create Free Account</h2>
            <form method="POST">
                <label>Shop / Username Name</label>
                <input type="text" name="shop_name" required placeholder="MyStore">
                <label>Phone / Gmail</label>
                <input type="text" name="phone" required placeholder="example@gmail.com">
                <label>Your UPI ID (For Withdrawal)</label>
                <input type="text" name="upi_id" required placeholder="yourname@okhdfcbank">
                <button type="submit" class="btn" style="width: 100%;">Register</button>
            </form>
            <p style="text-align: center; margin-top: 15px; font-size: 14px;">Already have an account? <a href="/login">Login here</a></p>
        </div>
    </div>
    """)

# 3. Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        shop = users_collection.find_one({"shop_name": shop_name})
        if shop:
            session["shop_name"] = shop_name
            return redirect(url_for("dashboard"))
        return "<script>alert('Shop not found!'); window.location='/login';</script>"
        
    return render_template_string(LAYOUT_CSS + """
    <div class="header"><a href="/" class="logo">💳 FamPay Gateway</a></div>
    <div class="container" style="max-width: 400px;">
        <div class="card">
            <h2>Welcome Back - Login</h2>
            <form method="POST">
                <label>Shop / Username</label>
                <input type="text" name="shop_name" required placeholder="MyStore">
                <button type="submit" class="btn" style="width: 100%;">Login</button>
            </form>
            <p style="text-align: center; margin-top: 15px; font-size: 14px;">Don't have an account? <a href="/signup">Register here</a></p>
        </div>
    </div>
    """)

# 4. User Dashboard (Overview, API Key, Payment Link, Withdrawals)
@app.route("/dashboard")
def dashboard():
    if "shop_name" not in session:
        return redirect(url_for("login"))
        
    shop = users_collection.find_one({"shop_name": session["shop_name"]})
    orders_count = orders_collection.count_documents({"shop_name": shop["shop_name"]})
    
    return render_template_string(LAYOUT_CSS + """
    <div class="header">
        <a href="/dashboard" class="logo">💳 FamPay Gateway ({{ shop.shop_name }})</a>
        <a href="/logout" style="color: red; text-decoration: none; font-weight: bold;">Logout</a>
    </div>
    <div class="container">
        <h2>Overview</h2>
        <div class="grid">
            <div class="stat-box">
                <p style="margin:0; color:#777;">Today's Orders</p>
                <h3 style="margin:5px 0 0 0;">0</h3>
            </div>
            <div class="stat-box">
                <p style="margin:0; color:#777;">Wallet Balance</p>
                <h3 style="margin:5px 0 0 0; color: green;">₹{{ shop.balance }}</h3>
            </div>
            <div class="stat-box">
                <p style="margin:0; color:#777;">All-Time Orders</p>
                <h3 style="margin:5px 0 0 0;">{{ orders_count }}</h3>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>🔑 Your API Key</h3>
            <input type="text" readonly value="{{ shop.api_key }}" style="background: #eee; font-family: monospace;">
        </div>
        
        <div class="card">
            <h3>🔗 Your Payment Link / Setup</h3>
            <p>Use this endpoint in your Telegram Bot:</p>
            <code style="background: #eee; padding: 10px; display: block; word-break: break-all;">{{ request.host_url }}api/create_order.php?amount=99&api_key={{ shop.api_key }}</code>
        </div>
        
        <div class="card">
            <h3>💸 Request Withdrawal (Min ₹10)</h3>
            <form action="/api/withdraw" method="POST">
                <input type="hidden" name="api_key" value="{{ shop.api_key }}">
                <label>Amount (₹)</label>
                <input type="number" name="amount" min="10" required placeholder="10">
                <label>Your UPI ID</label>
                <input type="text" name="upi_id" value="{{ shop.upi_id }}" required>
                <p style="font-size: 12px; color: #d9534f;">⚠️ Payment will be cleared within <b>10-12 hours</b> by Admin.</p>
                <button type="submit" class="btn">Request Withdrawal</button>
            </form>
        </div>
    </div>
    """, shop=shop, orders_count=orders_count)

@app.route("/logout")
def logout():
    session.pop("shop_name", None)
    return redirect(url_for("home"))

# 5. Withdrawal API handler
@app.route("/api/withdraw", methods=["POST"])
def request_withdrawal():
    api_key = request.form.get("api_key")
    amount = float(request.form.get("amount"))
    upi_id = request.form.get("upi_id")
    
    shop = users_collection.find_one({"api_key": api_key})
    if not shop or amount < 10:
        return "<script>alert('Invalid request or minimum amount is ₹10'); window.location='/dashboard';</script>"
        
    withdrawals_collection.insert_one({
        "shop_name": shop["shop_name"],
        "amount": amount,
        "upi_id": upi_id,
        "status": "pending"
    })
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": LOG_CHANNEL_ID,
            "text": f"<b>💸 Withdrawal Request!</b>\n🏪 Shop: {shop['shop_name']}\n💰 Amount: ₹{amount}\n💳 UPI: <code>{upi_id}</code>\n⏳ Clears in: 10-12 Hours",
            "parse_mode": "HTML"
        })
    except:
        pass
        
    return "<script>alert('Withdrawal request submitted successfully!'); window.location='/dashboard';</script>"

# 6. Create Order API (Bot ke liye)
@app.route("/api/create_order.php", methods=["GET"])
def create_order():
    amount = request.args.get("amount")
    api_key = request.args.get("api_key")
    
    if not amount or not api_key:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400
        
    shop = users_collection.find_one({"api_key": api_key})
    if not shop:
        return jsonify({"status": "error", "message": "Invalid API Key"}), 401
        
    order_id = "ORD" + uuid.uuid4().hex[:8].upper()
    qr_url = f"{request.host_url}checkout.php?order_id={order_id}"
    
    orders_collection.insert_one({
        "order_id": order_id,
        "shop_name": shop["shop_name"],
        "amount": float(amount),
        "status": "pending",
        "upi_id": shop["upi_id"]
    })
    
    return jsonify({
        "status": "success",
        "data": {
            "order_id": order_id,
            "qr_url": qr_url,
            "upi_id": shop["upi_id"],
            "amount": amount
        }
    })

# 7. Checkout Page
@app.route("/checkout.php")
def checkout_page():
    order_id = request.args.get("order_id")
    order = orders_collection.find_one({"order_id": order_id})
    if not order:
        return "<h3 style='text-align:center; color:red;'>❌ Invalid Order ID</h3>", 404
        
    return render_template_string(LAYOUT_CSS + """
    <div class="container" style="max-width: 400px; text-align: center;">
        <div class="card">
            <h2>💳 Complete Payment</h2>
            <p>Shop: <b>{{ order.shop_name }}</b></p>
            <h1 style="color: #27ae60;">₹{{ order.amount }}</h1>
            <p>Pay to UPI ID:</p>
            <p style="font-weight: bold; background: #eee; padding: 10px; word-break: break-all;">{{ order.upi_id }}</p>
            <button onclick="alert('Payment done! Go back to bot.')" class="btn" style="width: 100%;">Done</button>
        </div>
    </div>
    """, order=order)

# 8. Admin Panel
@app.route("/admin")
def admin_panel():
    key = request.args.get("key")
    if key != ADMIN_SECRET_KEY:
        return "<h3 style='color:red; text-align:center;'>❌ Unauthorized!</h3>", 403
        
    users = list(users_collection.find())
    withdrawals = list(withdrawals_collection.find({"status": "pending"}))
    
    return render_template_string(LAYOUT_CSS + """
    <div class="container">
        <h2>👑 Admin Control Panel</h2>
        <div class="card">
            <h3>📥 Pending Withdrawal Requests (10-12 Hours Window)</h3>
            {% if withdrawals %}
                <table border="1" cellpadding="10" style="width:100%; border-collapse: collapse;">
                    <tr style="background: #eee;"><th>Shop</th><th>Amount</th><th>UPI</th><th>Action</th></tr>
                    {% for w in withdrawals %}
                    <tr>
                        <td>{{ w.shop_name }}</td>
                        <td>₹{{ w.amount }}</td>
                        <td>{{ w.upi_id }}</td>
                        <td><a href="/admin/pay?id={{ w._id }}&key=admin123" class="btn" style="padding: 5px 10px; font-size: 12px;">Mark Paid</a></td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p>No pending withdrawals.</p>
            {% endif %}
        </div>
        <div class="card">
            <h3>👥 Total Registered Shops: {{ users|length }}</h3>
        </div>
    </div>
    """, users=users, withdrawals=withdrawals)

@app.route("/admin/pay")
def admin_pay():
    if request.args.get("key") != ADMIN_SECRET_KEY:
        return "Unauthorized", 403
    from bson.objectid import ObjectId
    w_id = request.args.get("id")
    withdrawals_collection.update_one({"_id": ObjectId(w_id)}, {"$set": {"status": "paid"}})
    return "<script>alert('Marked as Paid!'); window.location='/admin?key=admin123';</script>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
