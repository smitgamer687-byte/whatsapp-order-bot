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
WEBSITE_URL = os.environ.get('WEBSITE_URL', 'https://chefpal.preview.emergentagent.com')

# Payment Configuration
BASE_PAYMENT_LINK = 'https://pay0.shop/paylink?link=2296&amt='
SERVER_URL = os.environ.get('SERVER_URL', 'https://whatsapp-order-bot-vj1p.onrender.com')

# WhatsApp API URL
WHATSAPP_API_URL = f"https://graph.facebook.com/v23.0/{WHATSAPP_PHONE_ID}/messages"


class WhatsAppOrderBot:
    def __init__(self):
        self.user_states = {}
        self.payment_sessions = {}
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
            print(f"📤 Sending WhatsApp message to {phone_number}")
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
            print(f"📥 WhatsApp API Response: {response.status_code} - {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error sending message: {e}")
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

            buttons = ['Edit Order', 'Confirm Order']
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
        
        print(f"💾 Payment session created: {session_id}")
        print(f"📞 Phone: {normalized_phone}")
        print(f"💰 Amount: ₹{order_data.get('total', 0)}")
        
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
                    
                    # Create payment link with callback - FIXED URL
                    payment_url = f"{BASE_PAYMENT_LINK}{total}&redirect={SERVER_URL}/payment/callback?session={session_id}"
                    
                    message = f"""✅ Order Confirmed!

👤 Customer: {name}
🍽 Items: {food_items}
💰 Total: ₹{total}
🔖 Session ID: {session_id}

Click below to complete payment:"""

                    success = self.send_cta_button(phone_number, message, "Pay Now", payment_url)

                    # Update state
                    self.user_states[normalized_phone] = {
                        'stage': 'payment_pending',
                        'session_id': session_id,
                        'order_data': order_data
                    }

                    print(f"✅ Payment link sent with session: {session_id}")
                    print(f"🔗 Payment URL: {payment_url}")
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
            print(f"\n💳 Processing payment for session: {session_id}")
            
            if session_id not in self.payment_sessions:
                print(f"❌ Session not found: {session_id}")
                print(f"📋 Available sessions: {list(self.payment_sessions.keys())}")
                return False
            
            session = self.payment_sessions[session_id]
            normalized_phone = session['phone']
            order_data = session['order_data']
            
            print(f"✅ Session found!")
            print(f"📞 Phone: {normalized_phone}")
            
            # Get WhatsApp phone
            whatsapp_phone = self.format_phone_number(normalized_phone)
            print(f"📱 WhatsApp Phone: {whatsapp_phone}")
            
            # Generate order ID
            order_id = f"ORD{session_id}"
            
            # Get order details
            name = order_data.get('name', 'Customer')
            food_items = order_data.get('foodItems', 'N/A')
            quantity = order_data.get('quantity', 'N/A')
            total = order_data.get('total', 0)
            
            # Send order preparing message with full details
            message = f"""✅ Payment Received!

📋 ORDER DETAILS:
🔖 Order ID: {order_id}
👤 Name: {name}
🍽 Items: {food_items}
📊 Quantity: {quantity}
💰 Total: ₹{total}

👨‍🍳 Your order is being prepared
🕒 Estimated time: 15-20 minutes

Thank you for your order!
📞 Contact: +91-9327256068"""
            
            print(f"📤 Sending confirmation message...")
            success = self.send_whatsapp_message(whatsapp_phone, message)
            
            if success:
                print(f"✅ Payment confirmation sent to WhatsApp: {whatsapp_phone}")
            else:
                print(f"❌ Failed to send WhatsApp message to: {whatsapp_phone}")
            
            # Update session status
            self.payment_sessions[session_id]['status'] = 'completed'
            self.payment_sessions[session_id]['order_id'] = order_id
            
            # Clean up user state
            if normalized_phone in self.user_states:
                del self.user_states[normalized_phone]
            
            print(f"✅ Payment processed successfully for session: {session_id}")
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
    """Handle Pay0.shop payment callback - ALL METHODS"""
    try:
        print(f"\n{'='*70}")
        print(f"💳 PAYMENT CALLBACK RECEIVED")
        print(f"{'='*70}")
        print(f"Method: {request.method}")
        print(f"URL: {request.url}")
        print(f"Args: {dict(request.args)}")
        print(f"Form: {dict(request.form)}")
        print(f"Headers: {dict(request.headers)}")
        
        # Try to get JSON data
        json_data = request.get_json(silent=True) or {}
        print(f"JSON: {json_data}")
        
        # Get session ID from multiple sources
        session_id = (
            request.args.get('session') or 
            request.args.get('sessionId') or
            request.args.get('session_id') or
            request.form.get('session') or 
            request.form.get('sessionId') or
            json_data.get('session') or
            json_data.get('sessionId')
        )
        
        # Get payment status
        payment_status = (
            request.args.get('status') or 
            request.args.get('payment_status') or
            request.form.get('status') or 
            json_data.get('status', 'success')
        )
        
        print(f"\n📝 Extracted Data:")
        print(f"   Session ID: {session_id}")
        print(f"   Payment Status: {payment_status}")
        print(f"{'='*70}\n")
        
        if not session_id:
            print("❌ ERROR: Session ID missing!")
            print("   Redirecting to website...")
            return redirect(WEBSITE_URL)
        
        # Process payment if successful
        if payment_status.lower() in ['success', 'completed', 'paid', 'ok', '1', 'true', 'approved']:
            print(f"✅ Payment successful! Processing...")
            
            # Send WhatsApp message
            success = bot.process_payment_success(session_id)
            
            if success:
                print(f"✅ WhatsApp message sent successfully!")
            else:
                print(f"⚠️ Warning: WhatsApp message may have failed")
            
            # Get phone number for redirect
            session = bot.payment_sessions.get(session_id, {})
            phone = session.get('phone', '')
            
            print(f"\n🔄 Preparing WhatsApp redirect...")
            print(f"   Phone: {phone}")
            
            if phone:
                # Direct redirect to WhatsApp with pre-filled message
                whatsapp_link = f"https://wa.me/{phone}?text=Order%20confirmed!%20Thanks%20for%20payment."
                print(f"✅ Redirecting to: {whatsapp_link}")
                print(f"{'='*70}\n")
                return redirect(whatsapp_link)
            else:
                print(f"❌ ERROR: Phone number not found in session!")
                print(f"   Available sessions: {list(bot.payment_sessions.keys())}")
                print(f"   Redirecting to website...")
                return redirect(WEBSITE_URL)
        else:
            # Payment failed - redirect to website
            print(f"❌ Payment failed or cancelled: {payment_status}")
            print(f"   Redirecting to website...")
            return redirect(WEBSITE_URL)
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in payment callback!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"Redirecting to website...\n")
        return redirect(WEBSITE_URL)


# ALTERNATIVE ENDPOINTS - All redirect to main callback
@app.route('/webhook/payo-callback', methods=['GET', 'POST'])
def payo_callback():
    """Alternative callback endpoint - redirects to main"""
    print("⚠️ Warning: Old callback URL used. Redirecting to new endpoint...")
    return payment_callback()


@app.route('/payment/success', methods=['GET', 'POST'])
def payment_success():
    """Alternative success endpoint"""
    print("✅ Payment success endpoint called")
    return payment_callback()


@app.route('/payment/failure', methods=['GET', 'POST'])
def payment_failure():
    """Handle payment failure"""
    print("❌ Payment failed or cancelled")
    return redirect(WEBSITE_URL)


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


@app.route('/test/payment', methods=['GET'])
def test_payment():
    """Test payment callback"""
    session_id = request.args.get('session', 'TEST123456789')
    
    # Create test session
    bot.payment_sessions[session_id] = {
        'phone': '919876543210',
        'order_data': {
            'name': 'Test User',
            'foodItems': 'Test Pizza',
            'quantity': '1',
            'total': 99
        },
        'timestamp': datetime.now().strftime('%Y%m%d%H%M%S'),
        'status': 'pending'
    }
    
    print(f"🧪 Test payment session created: {session_id}")
    
    # Redirect to callback
    return redirect(f'/payment/callback?session={session_id}&status=success')


@app.route('/sessions', methods=['GET'])
def list_sessions():
    """List all active payment sessions"""
    return jsonify({
        'sessions': bot.payment_sessions,
        'user_states': bot.user_states,
        'count': len(bot.payment_sessions)
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
            'payo_callback': '/webhook/payo-callback (redirects to /payment/callback)',
            'test_order': '/test/order (POST)',
            'test_payment': '/test/payment',
            'sessions': '/sessions'
        },
        'config': {
            'website_url': WEBSITE_URL,
            'server_url': SERVER_URL,
            'payment_provider': 'Pay0.shop',
            'whatsapp_configured': bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)
        },
        'stats': {
            'active_sessions': len(bot.payment_sessions),
            'active_users': len(bot.user_states)
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
    print(f"   Alternative: {SERVER_URL}/webhook/payo-callback")
    
    print("\n📝 Payment Flow:")
    print("   1. Customer places order on website")
    print("   2. Bot sends order confirmation via WhatsApp")
    print("   3. Customer clicks 'Confirm Order'")
    print("   4. Bot sends Pay0 payment link with session ID")
    print("   5. Customer completes payment on Pay0.shop")
    print("   6. Pay0 redirects to callback URL with session ID")
    print("   7. Bot sends 'Order preparing' message to WhatsApp")
    print("   8. Customer automatically redirected to WhatsApp chat")
    
    print("\n🔧 Pay0.shop Configuration Required:")
    print(f"   ⚠️ IMPORTANT: Set this as your redirect URL in Pay0.shop:")
    print(f"   {SERVER_URL}/payment/callback")
    print(f"   ")
    print(f"   Alternative URLs (all work):")
    print(f"   - {SERVER_URL}/webhook/payo-callback")
    print(f"   - {SERVER_URL}/payment/success")
    
    print("\n🧪 Testing Endpoints:")
    print(f"   Health: {SERVER_URL}/health")
    print(f"   Test Order: {SERVER_URL}/test/order (POST)")
    print(f"   Test Payment: {SERVER_URL}/test/payment?session=TEST123")
    print(f"   View Sessions: {SERVER_URL}/sessions")
    
    print("\n📋 How to Test:")
    print("   1. Visit: {SERVER_URL}/test/payment")
    print("   2. Check if WhatsApp message is sent")
    print("   3. Check if redirect to WhatsApp works")
    
    print("\n🔍 Debugging Tips:")
    print("   - Check logs for 'PAYMENT CALLBACK RECEIVED'")
    print("   - Verify session ID is passed in URL")
    print("   - Check WhatsApp API response")
    print("   - View active sessions at /sessions endpoint")
    
    if all_set:
        print("\n✅ Bot is ready!")
        print(f"🌐 Website: {WEBSITE_URL}")
        print(f"🔗 Server: {SERVER_URL}")
        print("="*70 + "\n")
        print("🚀 Starting server on port 5000...")
        print("📱 Waiting for orders...\n")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("\n❌ Please set missing variables in Variables.env")
        print("\n📝 Required in Variables.env:")
        print("   WHATSAPP_TOKEN=your_whatsapp_token")
        print("   WHATSAPP_PHONE_ID=your_phone_id")
        print("   WEBSITE_URL=your_website_url")
        print("   SERVER_URL=https://whatsapp-order-bot-vj1p.onrender.com")
        print("\n⚠️ SERVER_URL must match your actual deployed URL!")
        print("="*70)


