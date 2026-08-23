from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
import uuid
import hashlib
import requests

app = Flask(__name__)

# ----------------- CONFIGURATION -----------------
# Apna MongoDB Atlas ka live URL yahan daalein
MONGO_URI = "mongodb+srv://your_mongo_user:your_password@cluster.mongodb.net/?retryWrites=true&w=majority"

# Apne Telegram Bot ka Token aur Channel/Group ID yahan daalein (Jahan signup ka alert aayega)
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
LOG_CHANNEL_ID = "-100xxxxxxxxxx" 
# -------------------------------------------------

client = MongoClient(MONGO_URI)
db = client["fampay_gateway"]
users_collection = db["users"]
orders_collection = db["orders"]

# 1. Home / Dashboard Page (Jahan log aayenge)
@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head>
        <title>FamPay Gateway Panel</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f4f4f9; text-align: center; padding: 50px; }
            .box { background: white; max-width: 500px; margin: auto; padding: 30px; border-radius: 10px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1); }
            code { background: #eee; padding: 3px 6px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🚀 FamPay Custom Gateway</h2>
            <p>Aapka apna payment gateway server successfully run ho raha hai!</p>
            <hr style="border: 0; border-top: 1px solid #ddd; margin: 20px 0;">
            <h3>API Documentation:</h3>
            <p><b>Create Order:</b><br><code>/api/create_order.php?amount=99&api_key=YOUR_KEY</code></p>
        </div>
    </body>
    </html>
    """)

# 2. Signup / Register API (Jab user site par shop banayega)
@app.route("/api/register", methods=["POST"])
def register_shop():
    data = request.json
    shop_name = data.get("shop_name")
    phone = data.get("phone") # Yahan phone ya gmail jo bhi user de
    upi_id = data.get("upi_id")
    
    if not shop_name or not phone or not upi_id:
        return jsonify({"status": "error", "message": "All fields are required"}), 400
        
    raw_key = f"{shop_name}_{phone}_{uuid.uuid4()}"
    api_key = "FAM_" + hashlib.sha256(raw_key.encode()).hexdigest()[:32].upper()
    
    # Database mein save karna
    users_collection.insert_one({
        "shop_name": shop_name,
        "phone": phone,
        "upi_id": upi_id,
        "api_key": api_key
    })
    
    # Telegram Channel par Signup ki notification bhejna
    log_message = (
        f"<b>🚨 New Gateway Registration!</b>\n\n"
        f"🏪 <b>Shop Name:</b> {shop_name}\n"
        f"📧 <b>Contact/Gmail:</b> {phone}\n"
        f"💳 <b>UPI ID:</b> <code>{upi_id}</code>\n"
        f"🔑 <b>API Key:</b> <code>{api_key}</code>"
    )
    
    try:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": LOG_CHANNEL_ID,
            "text": log_message,
            "parse_mode": "HTML"
        }
        requests.post(telegram_url, json=payload)
    except Exception as e:
        print(f"Telegram Notification Error: {e}")
    
    return jsonify({
        "status": "success",
        "message": "Shop registered successfully",
        "api_key": api_key
    })

# 3. Create Order API (Jisko aapka bot ya dusre developers call karenge)
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
    
    # Checkout page ka link generate karna
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

# 4. Checkout Page (Jahan member payment karega)
@app.route("/checkout.php")
def checkout_page():
    order_id = request.args.get("order_id")
    order = orders_collection.find_one({"order_id": order_id})
    
    if not order:
        return "<h3 style='text-align:center; margin-top:50px; color:red;'>❌ Invalid or Expired Order ID</h3>", 404
        
    return render_template_string("""
    <html>
    <head>
        <title>Checkout - FamPay Gateway</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; text-align: center; background: #f9f9f9; padding: 20px;">
        <div style="max-width: 400px; margin: auto; border: 1px solid #ddd; padding: 25px; border-radius: 12px; background: #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2>💳 Complete Payment</h2>
            <p style="color: #666; font-size: 14px;">Shop: <b>{{ order.shop_name }}</b></p>
            <p style="color: #666; font-size: 14px;">Order ID: <code>{{ order.order_id }}</code></p>
            <h1 style="color: #27ae60; margin: 20px 0;">₹{{ order.amount }}</h1>
            <div style="background: #f1f1f1; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="font-size: 13px; margin: 0; color: #444;">Pay to this UPI ID:</p>
                <p style="font-size: 16px; font-weight: bold; word-break: break-all; margin: 5px 0 0 0; color: #000;">{{ order.upi_id }}</p>
            </div>
            <button onclick="alert('Payment karne ke baad wapas bot par jakar status check karein!')" style="background: #27ae60; color: white; border: none; padding: 12px 20px; font-size: 15px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold;">Check Status</button>
        </div>
    </body>
    </html>
    """, order=order)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
  
