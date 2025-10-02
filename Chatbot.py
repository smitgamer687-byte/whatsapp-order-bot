from flask import Flask, request, jsonify, redirect
import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from flask_cors import CORS

# Load environment variables
load_dotenv('Variables.env')

app = Flask(__name__)

# CORS Configuration
CORS(app,
     origins=[
         "https://smitgamer687-byte.github.io",
         "http://localhost:*",
         "http://127.0.0.1:*",
         "https://pay0.shop"
     ],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=False,
     max_age=3600)

# WhatsApp Business API Configuration
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'your_verify_token')
WEBSITE_URL = os.environ.get('WEBSITE_URL', 'https://smitgamer687-byte.github.io/Hotelflow/')

# Payment Configuration
BASE_PAYMENT_LINK = 'https://pay0.shop/paylink?link=2296&amt='
# Your server URL for callback (update this with your actual server URL)
SERVER_URL = os.environ.get('SERVER_URL', 'https://your-server-url.com')

# WhatsApp API URL
WHATSAPP_API_URL = f"https://graph.facebook.com/v23.0/{WHATSAPP_PHONE_ID}/messages"


class WhatsAppOrderBot:
    def __init__(self):
        self.user_states = {}
        self.payment_sessions = {}  # Track payment sessions
        print("✅ WhatsAppOrderBot initialized with user_states")

    def normalize_phone_number(self, phone):
        """Normalize phone number for storage"""
        if not phone:
            return None
        phone = str(phone).strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        phone = phone.lstrip('0')
        
        if phone.startswith('91') and len(phone) == 12:
            return phone
        elif len(phone) == 10:
            return f"91{phone}"
        elif phone.startswith('91'):
            return phone
        else:
            return f"91{phone}"

    def format_phone_number(self, phone):
        """Format phone for WhatsApp API"""
        normalized = self.normalize_phone_number(phone)
        if normalized:
            return f"{normalized}"
        return None

    def send_whatsapp_message(self, phone_number, message):
        """Send text message via WhatsApp"""
        headers = {
            'Authorization': f'Bearer {WHATSAPP_TOKEN}',
            'Content-Type': 'application/json'
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }

        try:
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def send_cta_button(self, phone_number, message, button_text, website_url):
        """Send Call-to-Action button"""
        headers = {
            'Authorization': f'Bearer {WHATSAPP_TOKEN}',
            'Content-Type': 'application/json'
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "cta_url",
                "body": {"text": message},
                "action": {
                    "name": "cta_url",
                    "parameters": {
                        "display_text": button_text,
                        "url": website_url
                    }
                }
            }
        }

        try:
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                return True
            else:
                fallback_message = f"{message}\n\n🌐 {button_text}: {website_url}"
                return self.send_whatsapp_message(phone_number, fallback_message)
        except Exception as e:
            print(f"Error sending CTA: {e}")
            fallback_message = f"{message}\n\n🌐 {button_text}: {website_url}"
            return self.send_whatsapp_message(phone_number, fallback_message)

    def send_interactive_buttons(self, phone_number, message, buttons):
        """Send interactive buttons"""
        headers = {
            'Authorization': f'Bearer {WHATSAPP_TOKEN}',
            'Content-Type': 'application/json'
        }

        button_objects = []
        for i, button_text in enumerate(buttons):
            button_objects.append({
                "type": "reply",
                "reply": {
                    "id": f"btn_{i+1}",
                    "title": button_text[:20]
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {"buttons": button_objects}
            }
        }

        try:
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                return True
            else:
                return self.send_fallback_message(phone_number, message, buttons)
        except Exception as e:
            print(f"Error sending buttons: {e}")
            return self.send_fallback_message(phone_number, message, buttons)

    def send_fallback_message(self, phone_number, message, buttons):
        """Fallback text message"""
        fallback_message = message + "\n\n"
        for i, button in enumerate(buttons, 1):
            fallback_message += f"{i}. {button}\n"
        fallback_message += "\nReply with the number."
        return self.send_whatsapp_message(phone_number, fallback_message)

    def send_order_confirmation(self, order_data):
        """Send order confirmation with buttons"""
        try:
            if not hasattr(self, 'user_states'):
                self.user_states = {}
                
            print(f"\n📋 Processing order: {json.dumps(order_data, indent=2)}")

            name = order_data.get('name', 'Customer')
            phone = order_data.get('phone')
            food_items = order_data.get('foodItems', 'N/A')
            quantity = order_data.get('quantity', 'N/A')
            total = order_data.get('total', 0)
            timestamp = order_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M'))

            whatsapp_phone = self.format_phone_number(phone)
            normalized_phone = self.normalize_phone_number(phone)

            if not whatsapp_phone or not normalized_phone:
                print(f"❌ Invalid phone: {phone}")
                return False

            message = f"""🎉 Order Received!

📋 ORDER SUMMARY:
👤 Name: {name}
🍽 Items: {food_items}
📊 Quantity: {quantity}
💰 Total: ₹{total}
⏰ Time: {timestamp}

Please confirm your order:"""

            self.user_states[normalized_phone] = {
                'stage': 'awaiting_confirmation',
                'order_data': order_data,
                'whatsapp_phone': whatsapp_phone
            }

            buttons = ['✏ Edit Order', '✅ Confirm Order']
            success = self.send_interactive_buttons(whatsapp_phone, message, buttons)

            return success

        except Exception as e:
            print(f"❌ Error sending confirmation: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_payment_session(self, normalized_phone, order_data):
        """Generate unique payment session"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        session_id = f"{timestamp}{normalized_phone[-4:]}"
        
        self.payment_sessions[session_id] = {
            'phone': normalized_phone,
            'order_data': order_data,
            'timestamp': timestamp,
            'status': 'pending'
        }
        
        return session_id

    def handle_button_response(self, phone_number, button_id, button_text=None):
        """Handle button clicks"""
        try:
            if not hasattr(self, 'user_states'):
                self.user_states = {}
                
            normalized_phone = self.normalize_phone_number(phone_number)
            current_state = self.user_states.get(normalized_phone, {})

            if normalized_phone in self.user_states and current_state.get('stage') == 'awaiting_confirmation':
                order_data = current_state.get('order_data', {})

                # Edit Order
                if button_id == 'btn_1' or (button_text and 'edit' in button_text.lower()):
                    message = """✏ Edit Your Order

To make changes, visit our website below."""

                    self.send_cta_button(phone_number, message, "Visit Website", WEBSITE_URL)
                    
                    if normalized_phone in self.user_states:
                        del self.user_states[normalized_phone]
                    
                    return True

                # Confirm Order - Generate payment session and redirect
                elif button_id == 'btn_2' or (button_text and 'confirm' in button_text.lower()):
                    total = order_data.get('total', 0)
                    name = order_data.get('name', 'Customer')
                    food_items = order_data.get('foodItems', 'N/A')
                    
                    # Generate payment session ID
                    session_id = self.generate_payment_session(normalized_phone, order_data)
                    
                    # Create payment link with callback
                    payment_url = f"{BASE_PAYMENT_LINK}{total}&session={session_id}"
                    
                    message = f"""✅ Order Confirmed!

👤 Customer: {name}
🍽 Items: {food_items}
💰 Total: ₹{total}
🔖 Session ID: {session_id}

Click below to complete payment:"""

                    success = self.send_cta_button(phone_number, message, "💳 Pay Now", payment_url)

                    # Update state
                    self.user_states[normalized_phone] = {
                        'stage': 'payment_pending',
                        'session_id': session_id,
                        'order_data': order_data
                    }

                    print(f"✅ Payment link sent with session: {session_id}")
                    return success

            else:
                message = """Session expired.

Type 'hi' to start over."""
                self.send_whatsapp_message(phone_number, message)
                return True

        except Exception as e:
            print(f"❌ Error handling button: {e}")
            import traceback
            traceback.print_exc()
            return False

    def process_payment_success(self, session_id):
        """Process successful payment"""
        try:
            if session_id not in self.payment_sessions:
                print(f"❌ Session not found: {session_id}")
                return False
            
            session = self.payment_sessions[session_id]
            normalized_phone = session['phone']
            order_data = session['order_data']
            
            # Get WhatsApp phone
            whatsapp_phone = self.format_phone_number(normalized_phone)
            
            # Generate order ID
            order_id = f"ORD{session_id}"
            
            # Send order preparing message
            message = f"""✅ Payment Received!

🔖 Order ID: {order_id}
🍽 Your order is being prepared
🕒 Estimated time: 15-20 minutes

Thank you for your order!
📞 Contact: +91-9327256068"""
            
            success = self.send_whatsapp_message(whatsapp_phone, message)
            
            # Update session status
            self.payment_sessions[session_id]['status'] = 'completed'
            self.payment_sessions[session_id]['order_id'] = order_id
            
            # Clean up user state
            if normalized_phone in self.user_states:
                del self.user_states[normalized_phone]
            
            print(f"✅ Payment processed for session: {session_id}")
            return success
            
        except Exception as e:
            print(f"❌ Error processing payment: {e}")
            import traceback
            traceback.print_exc()
            return False

    def handle_basic_messages(self, phone_number, message_body):
        """Handle basic messages"""
        message_body = str(message_body).lower().strip()
        normalized_phone = self.normalize_phone_number(phone_number)

        if not hasattr(self, 'user_states'):
            self.user_states = {}

        # Check if in confirmation flow
        if normalized_phone in self.user_states:
            current_state = self.user_states[normalized_phone]
            
            if current_state.get('stage') == 'awaiting_confirmation':
                if '1' in message_body or 'edit' in message_body:
                    return self.handle_button_response(phone_number, 'btn_1', 'edit')
                elif '2' in message_body or 'confirm' in message_body:
                    return self.handle_button_response(phone_number, 'btn_2', 'confirm')

        # Greetings
        if any(kw in message_body for kw in ['hi', 'hello', 'hey', 'hy']):
            message = """🍕 Welcome to our restaurant!

To place your order, click below:"""
            self.send_cta_button(phone_number, message, "Order Now", WEBSITE_URL)
            return True

        # Menu
        elif 'menu' in message_body:
            message = """📋 Our Menu

View full menu with prices:"""
            self.send_cta_button(phone_number, message, "View Menu", WEBSITE_URL)
            return True

        # Status/Payment
        elif 'status' in message_body or 'order' in message_body:
            message = """📋 Order Status

For order updates, contact:
📞 +91-9327256068"""
            self.send_whatsapp_message(phone_number, message)
            return True

        # Help
        elif 'help' in message_body or 'support' in message_body:
            message = """🆘 Support

📞 Call: +91-9327256068
🕒 Hours: 9 AM - 11 PM

Commands:
• 'hi' - Place order
• 'menu' - View menu
• 'status' - Order status"""
            self.send_whatsapp_message(phone_number, message)
            return True

        # Default
        else:
            message = """Hi! 👋

Commands:
• 'hi' - Place order
• 'menu' - View menu
• 'status' - Order status
• 'help' - Get support

Ready to order? Type 'hi'!"""
            self.send_whatsapp_message(phone_number, message)
            return True


# Initialize bot GLOBALLY
bot = WhatsAppOrderBot()

print(f"🤖 Bot initialized: {hasattr(bot, 'user_states')}")
print(f"📊 User states type: {type(getattr(bot, 'user_states', None))}")


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response, 200


@app.route('/webhook/google-sheets', methods=['POST', 'OPTIONS'])
def google_sheets_webhook():
    """Handle Google Sheets webhook"""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.json
        print(f"📥 Google Sheets webhook: {json.dumps(data, indent=2)}")

        order_data = data.get('order', {})
        timestamp = data.get('timestamp', datetime.now().isoformat())

        if order_data and order_data.get('name') and order_data.get('phone'):
            order_data['timestamp'] = timestamp
            success = bot.send_order_confirmation(order_data)

            return jsonify({
                'success': success,
                'message': 'Order processed',
                'timestamp': timestamp
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid order data'
            }), 400

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/payment/callback', methods=['GET', 'POST'])
def payment_callback():
    """Handle Pay0.shop payment callback"""
    try:
        print(f"💳 Payment callback received")
        
        # Get session ID from query params or form data
        session_id = request.args.get('session') or request.form.get('session')
        payment_status = request.args.get('status') or request.form.get('status', 'success')
        
        print(f"Session ID: {session_id}, Status: {payment_status}")
        
        if not session_id:
            return jsonify({'error': 'Session ID missing'}), 400
        
        # Process payment if successful
        if payment_status.lower() in ['success', 'completed', 'paid']:
            success = bot.process_payment_success(session_id)
            
            if success:
                # Create WhatsApp deep link to redirect back to chat
                session = bot.payment_sessions.get(session_id, {})
                phone = session.get('phone', '')
                
                # WhatsApp deep link (opens WhatsApp app)
                whatsapp_link = f"https://wa.me/{phone}"
                
                # Return HTML page with auto-redirect
                return f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Payment Successful</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 50px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                        }}
                        .container {{
                            background: white;
                            color: #333;
                            padding: 40px;
                            border-radius: 20px;
                            max-width: 400px;
                            margin: 0 auto;
                            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                        }}
                        .success-icon {{
                            font-size: 80px;
                            margin-bottom: 20px;
                        }}
                        h1 {{
                            color: #28a745;
                            margin-bottom: 20px;
                        }}
                        .btn {{
                            display: inline-block;
                            padding: 15px 30px;
                            background: #25D366;
                            color: white;
                            text-decoration: none;
                            border-radius: 30px;
                            font-weight: bold;
                            margin-top: 20px;
                            transition: transform 0.2s;
                        }}
                        .btn:hover {{
                            transform: scale(1.05);
                        }}
                        .info {{
                            margin: 20px 0;
                            color: #666;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">✅</div>
                        <h1>Payment Successful!</h1>
                        <p class="info">Your order is being prepared</p>
                        <p class="info">Order ID: <strong>ORD{session_id}</strong></p>
                        <p>Redirecting to WhatsApp...</p>
                        <a href="{whatsapp_link}" class="btn">Open WhatsApp</a>
                    </div>
                    <script>
                        // Auto-redirect after 3 seconds
                        setTimeout(function() {{
                            window.location.href = "{whatsapp_link}";
                        }}, 3000);
                    </script>
                </body>
                </html>
                """
            else:
                return jsonify({'error': 'Failed to process payment'}), 500
        else:
            return jsonify({'error': 'Payment failed or cancelled'}), 400
            
    except Exception as e:
        print(f"❌ Error in payment callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/payment/success', methods=['GET'])
def payment_success():
    """Alternative success endpoint"""
    return payment_callback()


@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    """Handle WhatsApp webhook"""
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if verify_token == VERIFY_TOKEN:
            return challenge
        else:
            return 'Invalid token', 403

    elif request.method == 'POST':
        try:
            data = request.json
            print(f"📥 WhatsApp webhook: {json.dumps(data, indent=2)}")

            if 'entry' in data:
                for entry in data['entry']:
                    for change in entry.get('changes', []):
                        if change.get('field') == 'messages':
                            messages = change.get('value', {}).get('messages', [])

                            for message in messages:
                                phone_number = message['from']

                                if message.get('type') == 'text':
                                    message_body = message['text']['body']
                                    bot.handle_basic_messages(phone_number, message_body)

                                elif message.get('type') == 'interactive':
                                    if 'button_reply' in message['interactive']:
                                        button_reply = message['interactive']['button_reply']
                                        button_id = button_reply['id']
                                        button_text = button_reply.get('title', '')
                                        bot.handle_button_response(phone_number, button_id, button_text)

            return jsonify({'status': 'success'}), 200

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500


@app.route('/test/order', methods=['POST'])
def test_order():
    """Test order confirmation"""
    data = request.json or {}
    
    sample_order = {
        'name': data.get('name', 'Test Customer'),
        'phone': data.get('phone', '9876543210'),
        'foodItems': data.get('foodItems', 'Pizza, Coke'),
        'quantity': data.get('quantity', '1, 2'),
        'total': data.get('total', 99),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    
    print(f"\n🧪 Testing order confirmation...")
    success = bot.send_order_confirmation(sample_order)
    
    return jsonify({
        'success': success,
        'test_data': sample_order,
        'message': 'Order confirmation sent to WhatsApp' if success else 'Failed to send'
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'WhatsApp Order Bot with Pay0 Integration',
        'endpoints': {
            'google_sheets': '/webhook/google-sheets',
            'whatsapp': '/webhook/whatsapp',
            'payment_callback': '/payment/callback',
            'test_order': '/test/order (POST)'
        },
        'config': {
            'website_url': WEBSITE_URL,
            'server_url': SERVER_URL,
            'payment_provider': 'Pay0.shop',
            'whatsapp_configured': bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)
        }
    })


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🤖 WhatsApp Order Bot with Pay0.shop Integration")
    print("="*70)
    
    required_vars = {
        'WHATSAPP_TOKEN': WHATSAPP_TOKEN,
        'WHATSAPP_PHONE_ID': WHATSAPP_PHONE_ID,
        'WEBSITE_URL': WEBSITE_URL,
        'SERVER_URL': SERVER_URL
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value and var_value != 'https://your-server-url.com':
            if 'TOKEN' in var_name:
                masked = '*' * 20 + (var_value[-8:] if len(var_value) > 8 else var_value[-4:])
                print(f"✅ {var_name}: {masked}")
            else:
                print(f"✅ {var_name}: {var_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            if var_name != 'SERVER_URL':
                all_set = False
    
    print("\n💳 Payment Configuration:")
    print(f"   Payment Provider: Pay0.shop")
    print(f"   Base Link: {BASE_PAYMENT_LINK}")
    print(f"   Callback URL: {SERVER_URL}/payment/callback")
    
    print("\n📝 Payment Flow:")
    print("   1. Customer places order on website")
    print("   2. Bot sends order confirmation via WhatsApp")
    print("   3. Customer clicks 'Confirm Order'")
    print("   4. Bot sends Pay0 payment link with session ID")
    print("   5. Customer completes payment on Pay0.shop")
    print("   6. Pay0 redirects to callback URL")
    print("   7. Bot sends 'Order preparing' message")
    print("   8. Customer redirected back to WhatsApp")
    
    print("\n🔧 Setup Pay0.shop:")
    print(f"   1. Set callback URL: {SERVER_URL}/payment/callback")
    print(f"   2. Ensure redirect includes session parameter")
    
    print("\n🔧 Test Endpoints:")
    print(f"   Health Check: http://localhost:5000/health")
    print(f"   Test Order: http://localhost:5000/test/order")
    
    if all_set:
        print("\n✅ Bot is ready!")
        print(f"🌐 Website: {WEBSITE_URL}")
        print("="*70 + "\n")
        app.run(debug=False, host='0.0.0.0', port=5000)
    else:
        print("\n❌ Please set missing variables in Variables.env")
        print("\n📝 Required in Variables.env:")
        print("   WHATSAPP_TOKEN=your_whatsapp_token")
        print("   WHATSAPP_PHONE_ID=your_phone_id")
        print("   WEBSITE_URL=your_website_url")
        print("   SERVER_URL=your_server_url (e.g., https://yourdomain.com)")
        print("="*70)
