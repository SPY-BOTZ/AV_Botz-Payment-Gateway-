from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
import uuid
import hashlib
import requests

app = Flask(__name__)

# ----------------- CONFIGURATION -----------------
MONGO_URI = "mongodb+srv://wajsarif461_db_user:TwacJh76mwpHHpjw@cluster0.biueyst.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
TELEGRAM_BOT_TOKEN = "8432557033:AAGts8uHMdhRVaNFTHX3_tp2VYUEZQGEr78"
LOG_CHANNEL_ID = "-1002580860502" 
ADMIN_SECRET_KEY = "admin123"  # Admin panel access karne ke liye password
# -------------------------------------------------

client = MongoClient(MONGO_URI)
db = client["fampay_gateway"]
users_collection = db["users"]
orders_collection = db["orders"]
withdrawals_collection = db["withdrawals"]

# 1. Home / Dashboard Page (With Withdraw Option)
@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head><title>FamPay Gateway Panel</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; text-align: center; padding: 30px; background: #f4f4f9;">
        <div style="max-width: 450px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
            <h2>🚀 FamPay Custom Gateway</h2>
            <p>Aapka gateway server successfully run ho raha hai!</p>
            <hr style="border: 0; border-top: 1px solid #ddd; margin: 20px 0;">
            <h3>💸 Request Withdrawal</h3>
            <form action="/api/withdraw" method="POST" style="text-align: left;">
                <label style="font-size: 14px; font-weight: bold;">API Key / Shop Token:</label><br>
                <input type="text" name="api_key" placeholder="FAM_..." required style="width: 100%; padding: 8px; margin: 5px 0 15px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                
                <label style="font-size: 14px; font-weight: bold;">Withdrawal Amount (Min ₹10):</label><br>
                <input type="number" name="amount" placeholder="10" min="10" required style="width: 100%; padding: 8px; margin: 5px 0 15px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                
                <label style="font-size: 14px; font-weight: bold;">Your UPI ID:</label><br>
                <input type="text" name="upi_id" placeholder="yourname@okhdfcbank" required style="width: 100%; padding: 8px; margin: 5px 0 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                
                <p style="font-size: 12px; color: #d9534f; margin-bottom: 15px;">⚠️ <b>Note:</b> Maximum/Minimum withdrawal limit is ₹10. Payment will be cleared within <b>10-12 hours</b>.</p>
                
                <button type="submit" style="background: #27ae60; color: white; border: none; padding: 10px; width: 100%; border-radius: 5px; font-weight: bold; cursor: pointer;">Submit Request</button>
            </form>
            <br>
            <p><a href="/admin?key=admin123" style="color: #333; font-size: 14px;">🔑 Go to Admin Panel</a></p>
        </div>
    </body>
    </html>
    """)

# 2. Withdrawal Request API
@app.route("/api/withdraw", methods=["POST"])
def request_withdrawal():
    api_key = request.form.get("api_key")
    amount = request.form.get("amount")
    upi_id = request.form.get("upi_id")
    
    if not api_key or not amount or not upi_id:
        return "<h3 style='color:red; text-align:center; margin-top:50px;'>❌ All fields are required! <a href='/'>Go Back</a></h3>", 400
        
    try:
        amount = float(amount)
    except ValueError:
        return "<h3 style='color:red; text-align:center; margin-top:50px;'>❌ Invalid amount! <a href='/'>Go Back</a></h3>", 400
        
    if amount < 10:
        return "<h3 style='color:red; text-align:center; margin-top:50px;'>❌ Minimum withdrawal amount is ₹10! <a href='/'>Go Back</a></h3>", 400
        
    shop = users_collection.find_one({"api_key": api_key})
    if not shop:
        return "<h3 style='color:red; text-align:center; margin-top:50px;'>❌ Invalid API Key! <a href='/'>Go Back</a></h3>", 401
        
    # Check balance (agar aapne balance track kiya hai)
    current_balance = shop.get("balance", 0.0)
    if current_balance < amount:
        return f"<h3 style='color:red; text-align:center; margin-top:50px;'>❌ Insufficient Balance! Your balance is ₹{current_balance}. <a href='/'>Go Back</a></h3>", 400
        
    # Save withdrawal request
    withdrawals_collection.insert_one({
        "shop_name": shop["shop_name"],
        "amount": amount,
        "upi_id": upi_id,
        "status": "pending"
    })
    
    # Telegram Notification for Withdrawal
    log_message = (
        f"<b>💸 New Withdrawal Request!</b>\n\n"
        f"🏪 <b>Shop Name:</b> {shop['shop_name']}\n"
        f"💰 <b>Amount:</b> ₹{amount}\n"
        f"💳 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"⏳ <b>Clearing Time:</b> 10-12 Hours"
    )
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": LOG_CHANNEL_ID,
            "text": log_message,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"Telegram Error: {e}")
        
    return "<h3 style='color:green; text-align:center; margin-top:50px;'>✅ Withdrawal request submitted successfully! It will be cleared within 10-12 hours. <br><br><a href='/'>Go Home</a></h3>"

# 3. Admin Panel
@app.route("/admin")
def admin_panel():
    key = request.args.get("key")
    if key != ADMIN_SECRET_KEY:
        return "<h3 style='color:red; text-align:center; margin-top:50px;'>❌ Unauthorized Access! Wrong Admin Key.</h3>", 403
        
    users = list(users_collection.find())
    withdrawals = list(withdrawals_collection.find({"status": "pending"}))
    
    return render_template_string("""
    <html>
    <head>
        <title>Admin Panel - FamPay Gateway</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial; background: #f4f4f9; padding: 20px;">
        <div style="max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <h2>👑 Admin Control Panel</h2>
            <hr>
            <h3>📥 Pending Withdrawal Requests (10-12 Hours Window)</h3>
            {% if withdrawals %}
                <table border="1" cellpadding="10" style="width:100%; border-collapse: collapse; text-align: left;">
                    <tr style="background: #eee;">
                        <th>Shop Name</th>
                        <th>Amount</th>
                        <th>UPI ID</th>
                        <th>Action</th>
                    </tr>
                    {% for w in withdrawals %}
                    <tr>
                        <td>{{ w.shop_name }}</td>
                        <td>₹{{ w.amount }}</td>
                        <td>{{ w.upi_id }}</td>
                        <td>
                            <a href="/admin/pay?id={{ w._id }}&key=admin123" style="background: green; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px;">Mark Paid</a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p>No pending withdrawal requests.</p>
            {% endif %}
            
            <h3 style="margin-top: 30px;">👥 Registered Users/Shops</h3>
            <p>Total Shops: <b>{{ users|length }}</b></p>
        </div>
    </body>
    </html>
    """, users=users, withdrawals=withdrawals)

# 4. Mark Withdrawal as Paid
@app.route("/admin/pay")
def admin_pay():
    key = request.args.get("key")
    if key != ADMIN_SECRET_KEY:
        return "Unauthorized", 403
        
    from bson.objectid import ObjectId
    w_id = request.args.get("id")
    
    withdrawals_collection.update_one({"_id": ObjectId(w_id)}, {"$set": {"status": "paid"}})
    return "<script>alert('Marked as Paid successfully!'); window.location='/admin?key=admin123';</script>"

# 5. Signup API
@app.route("/api/register", methods=["POST"])
def register_shop():
    data = request.json
    shop_name = data.get("shop_name")
    phone = data.get("phone")
    upi_id = data.get("upi_id")
    
    if not shop_name or not phone or not upi_id:
        return jsonify({"status": "error", "message": "All fields are required"}), 400
        
    raw_key = f"{shop_name}_{phone}_{uuid.uuid4()}"
    api_key = "FAM_" + hashlib.sha256(raw_key.encode()).hexdigest()[:32].upper()
    
    users_collection.insert_one({
        "shop_name": shop_name,
        "phone": phone,
        "upi_id": upi_id,
        "api_key": api_key,
        "balance": 0.0  # Initial balance
    })
    
    log_message = (
        f"<b>🚨 New Gateway Registration!</b>\n\n"
        f"🏪 <b>Shop Name:</b> {shop_name}\n"
        f"📧 <b>Contact/Gmail:</b> {phone}\n"
        f"💳 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"🔑 <b>API Key:</b> <code>{api_key}</code>"
    )
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": LOG_CHANNEL_ID,
            "text": log_message,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"Telegram Error: {e}")
    
    return jsonify({"status": "success", "message": "Shop registered successfully", "api_key": api_key})

# 6. Create Order API
@app.route("/api/create_order.php", methods=["GET"])
def create_order():
    amount = request.args.get("amount")
    api_key = request.args.get("api_key")
    
    if not amount or not api_key:
        return jsonify({"status": "error", "message": "Missing amount or api_key"}), 400
        
    shop = users_collection.find_one({"api_key": api_key})
    if not shop:
        return jsonify({"status": "error", "message": "Invalid API Key"}), 401
        
    order_id = "ORD" + uuid.uuid4().hex[:8].upper()
    request_host = request.host_url
    qr_url = f"{request_host}checkout.php?order_id={order_id}"
    
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
        
    return render_template_string("""
    <html>
    <head><title>Checkout</title><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="font-family: Arial; text-align: center; background: #f9f9f9; padding: 20px;">
        <div style="max-width: 400px; margin: auto; border: 1px solid #ddd; padding: 25px; border-radius: 12px; background: #fff;">
            <h2>💳 Complete Payment</h2>
            <p>Shop: <b>{{ order.shop_name }}</b></p>
            <h1 style="color: #27ae60;">₹{{ order.amount }}</h1>
            <p>Pay to UPI ID:</p>
            <p style="font-weight: bold; background: #eee; padding: 10px;">{{ order.upi_id }}</p>
            <button onclick="alert('Payment done! Go back to bot.')" style="background: #27ae60; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; cursor: pointer;">Done</button>
        </div>
    </body>
    </html>
    """, order=order)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
