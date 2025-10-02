from flask import Flask, request, jsonify
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
         "http://127.0.0.1:*"
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

# Pay0.shop Configuration - CORRECTED
# IMPORTANT: Get your REAL API key from Pay0.shop dashboard
PAYO_USER_TOKEN = os.environ.get('PAYO_API_KEY')  # This must be set in Variables.env
PAYO_BASE_URL = 'https://pay0.shop'
PAYO_WEBHOOK_URL = 'https://smitgamer687.pythonanywhere.com/webhook/payo-callback'

# WhatsApp API URL
WHATSAPP_API_URL = f"https://graph.facebook.com/v23.0/{WHATSAPP_PHONE_ID}/messages"


class Pay0PaymentGateway:
    """Handle Pay0.shop payment gateway integration - FULLY CORRECTED"""
    
    def __init__(self):
        self.base_url = PAYO_BASE_URL
        self.user_token = PAYO_USER_TOKEN
        self.webhook_url = PAYO_WEBHOOK_URL
        
        # Validate API key is set
        if not self.user_token:
            print("⚠️ WARNING: PAYO_API_KEY not set in environment!")
    
    def create_payment_link(self, order_data):
        """Create payment link using Pay0.shop API"""
        try:
            # Validate API key first
            if not self.user_token:
                print("❌ CRITICAL: API Key not configured!")
                return None
            
            # Extract and normalize phone
            customer_phone = str(order_data.get('phone', '')).replace('+', '').replace('-', '').replace(' ', '')
            if not customer_phone.startswith('91') and len(customer_phone) == 10:
                customer_phone = '91' + customer_phone
            
            # Extract 10-digit mobile (last 10 digits)
            customer_mobile = customer_phone[-10:] if len(customer_phone) > 10 else customer_phone
            
            # Ensure mobile is exactly 10 digits
            if len(customer_mobile) != 10:
                print(f"❌ Invalid mobile number: {customer_mobile}")
                return None
            
            # Get amount and convert to integer string
            amount = str(int(float(order_data.get('total', 0))))
            
            # Generate unique order ID
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            order_id = f"ORD{timestamp}{customer_mobile[-4:]}"
            
            customer_name = order_data.get('name', 'Customer')
            food_items = order_data.get('foodItems', 'Food Order')
            
            # API Endpoint
            endpoint = f"{self.base_url}/api/create-order"
            
            # Prepare payload - Form-encoded as per Pay0.shop docs
            payload = {
                "customer_mobile": customer_mobile,  # Must be 10 digits
                "customer_name": customer_name,
                "user_token": self.user_token,  # Your API key from dashboard
                "amount": amount,
                "order_id": order_id,
                "redirect_url": WEBSITE_URL,
                "remark1": food_items[:100],
                "remark2": f"Phone: {customer_phone}"
            }
            
            # Headers - Form-encoded
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            print("\n" + "="*70)
            print("🔄 Creating Pay0.shop Payment Link")
            print("="*70)
            print(f"📍 Endpoint: {endpoint}")
            print(f"🔖 Order ID: {order_id}")
            print(f"💰 Amount: ₹{amount}")
            print(f"📱 Customer Mobile: {customer_mobile}")
            print(f"👤 Customer Name: {customer_name}")
            print(f"🍽️ Items: {food_items}")
            print(f"🔑 API Key (last 8): ...{self.user_token[-8:] if self.user_token else 'NOT SET'}")
            print("="*70)
            
            # Make API request
            response = requests.post(endpoint, data=payload, headers=headers, timeout=15)
            
            print(f"\n📤 Response Status: {response.status_code}")
            print(f"📤 Response Body: {response.text}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                except:
                    print("❌ Failed to parse JSON response")
                    return None
                
                # Check for success - Pay0.shop returns {"status": true, ...}
                if response_data.get('status') == True:
                    result = response_data.get('result', {})
                    payment_url = result.get('payment_url')
                    
                    if payment_url:
                        print(f"\n✅ SUCCESS! Payment link created")
                        print(f"🔗 Payment URL: {payment_url}")
                        print("="*70 + "\n")
                        
                        return {
                            'success': True,
                            'payment_link': payment_url,
                            'order_id': order_id,
                            'amount': amount,
                            'customer_phone': customer_phone
                        }
                    else:
                        print("❌ No payment_url in response")
                        print(f"Response: {response_data}")
                        return None
                else:
                    error_msg = response_data.get('message', 'Unknown error')
                    print(f"❌ Pay0 API Error: {error_msg}")
                    print(f"Full response: {response_data}")
                    return None
            else:
                print(f"❌ HTTP Error {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ Request timeout (15s)")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def check_payment_status(self, order_id):
        """Check payment status from Pay0.shop"""
        try:
            url = f"{self.base_url}/api/check-order-status"
            
            payload = {
                "user_token": self.user_token,
                "order_id": order_id
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            print(f"\n📊 Checking status for order: {order_id}")
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            
            print(f"📊 Status Response: {response.status_code}")
            print(f"📊 Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == True:
                    txn_data = result.get('result', {})
                    return {
                        'status': txn_data.get('txnStatus', 'UNKNOWN'),
                        'order_id': txn_data.get('orderId'),
                        'amount': txn_data.get('amount'),
                        'date': txn_data.get('date'),
                        'utr': txn_data.get('utr', 'N/A')
                    }
                else:
                    return {
                        'status': 'ERROR',
                        'message': result.get('message', 'Unknown error')
                    }
            else:
                return {"status": "ERROR", "message": "API request failed"}
                
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return {"status": "ERROR", "message": str(e)}


class WhatsAppOrderBot:
    def __init__(self):
        self.user_states = {}
        self.payment_gateway = Pay0PaymentGateway()

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
🍽️ Items: {food_items}
📊 Quantity: {quantity}
💰 Total: ₹{total}
⏰ Time: {timestamp}

Please confirm your order:"""

            self.user_states[normalized_phone] = {
                'stage': 'awaiting_confirmation',
                'order_data': order_data,
                'whatsapp_phone': whatsapp_phone
            }

            buttons = ['✏️ Edit Order', '✅ Confirm Order']
            success = self.send_interactive_buttons(whatsapp_phone, message, buttons)

            return success

        except Exception as e:
            print(f"❌ Error sending confirmation: {e}")
            import traceback
            traceback.print_exc()
            return False

    def handle_button_response(self, phone_number, button_id, button_text=None):
        """Handle button clicks"""
        try:
            normalized_phone = self.normalize_phone_number(phone_number)
            current_state = self.user_states.get(normalized_phone, {})

            if normalized_phone in self.user_states and current_state.get('stage') == 'awaiting_confirmation':
                order_data = current_state.get('order_data', {})

                # Edit Order
                if button_id == 'btn_1' or (button_text and 'edit' in button_text.lower()):
                    message = """✏️ Edit Your Order

To make changes, visit our website below."""

                    self.send_cta_button(phone_number, message, "Visit Website", WEBSITE_URL)
                    
                    if normalized_phone in self.user_states:
                        del self.user_states[normalized_phone]
                    
                    return True

                # Confirm Order
                elif button_id == 'btn_2' or (button_text and 'confirm' in button_text.lower()):
                    total = order_data.get('total', 0)
                    name = order_data.get('name', 'Customer')
                    food_items = order_data.get('foodItems', 'N/A')

                    print(f"\n💳 Creating payment link for order...")
                    print(f"   Amount: ₹{total}")
                    print(f"   Customer: {name}")
                    
                    # Create payment link
                    payment_result = self.payment_gateway.create_payment_link(order_data)

                    if payment_result and payment_result.get('success'):
                        payment_link = payment_result['payment_link']
                        order_id = payment_result['order_id']

                        message = f"""✅ Order Confirmed!

👤 Customer: {name}
🍽️ Items: {food_items}
💰 Total: ₹{total}
🔖 Order ID: {order_id}

🎫 Order being prepared!
📞 Queries: +91-9327256068
🕒 Time: 15-20 minutes

Click below to pay securely:"""

                        success = self.send_cta_button(phone_number, message, "💳 Pay Now", payment_link)

                        self.user_states[normalized_phone] = {
                            'stage': 'payment_pending',
                            'order_id': order_id,
                            'payment_link': payment_link,
                            'order_data': order_data
                        }

                        print(f"✅ Payment link sent successfully!")
                        return success
                    else:
                        error_message = """❌ Payment Link Error

Couldn't generate payment link.

📞 Contact: +91-9327256068"""

                        self.send_whatsapp_message(phone_number, error_message)
                        
                        if normalized_phone in self.user_states:
                            del self.user_states[normalized_phone]
                        
                        print(f"❌ Failed to create payment link")
                        return False

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

    def handle_basic_messages(self, phone_number, message_body):
        """Handle basic messages"""
        message_body = str(message_body).lower().strip()
        normalized_phone = self.normalize_phone_number(phone_number)

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

        # Status
        elif 'status' in message_body or 'payment' in message_body:
            if normalized_phone in self.user_states:
                state = self.user_states[normalized_phone]
                if state.get('stage') == 'payment_pending' and state.get('order_id'):
                    order_id = state['order_id']
                    status_result = self.payment_gateway.check_payment_status(order_id)
                    
                    status = status_result.get('status', 'UNKNOWN')
                    utr = status_result.get('utr', 'N/A')
                    
                    message = f"""📊 Payment Status

🔖 Order ID: {order_id}
💳 Status: {status}
🔢 UTR: {utr}

Contact: +91-9327256068"""
                    self.send_whatsapp_message(phone_number, message)
                    return True

            message = """Provide order ID or contact:

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
• 'status' - Check payment"""
            self.send_whatsapp_message(phone_number, message)
            return True

        # Default
        else:
            message = """Hi! 👋

Commands:
• 'hi' - Place order
• 'menu' - View menu
• 'status' - Check payment
• 'help' - Get support

Ready to order? Type 'hi'!"""
            self.send_whatsapp_message(phone_number, message)
            return True


# Initialize bot
bot = WhatsAppOrderBot()


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'https://smitgamer687-byte.github.io')
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


@app.route('/webhook/payo-callback', methods=['POST'])
def payo_webhook_callback():
    """Handle Pay0.shop payment callback webhook"""
    try:
        data = request.form.to_dict()
        print(f"\n💳 Pay0 Webhook Received")
        print("="*70)
        print(json.dumps(data, indent=2))
        print("="*70)

        status = data.get('status')
        order_id = data.get('order_id')
        amount = data.get('amount')
        customer_mobile = data.get('customer_mobile')

        if status == 'SUCCESS':
            customer_phone = None
            for phone, state in bot.user_states.items():
                if state.get('order_id') == order_id:
                    customer_phone = phone
                    break

            if customer_phone:
                whatsapp_phone = bot.format_phone_number(customer_phone)
                success_message = f"""✅ Payment Successful!

🔖 Order ID: {order_id}
💰 Amount: ₹{amount}

🎉 Thank you for your payment!
🍽️ Your order is being prepared
🕒 Estimated delivery: 15-20 minutes

For queries: +91-9327256068"""

                bot.send_whatsapp_message(whatsapp_phone, success_message)

                if customer_phone in bot.user_states:
                    del bot.user_states[customer_phone]
                
                print(f"✅ Success notification sent to {customer_phone}")
            else:
                print(f"⚠️ Customer phone not found for order {order_id}")

            return "Webhook received successfully", 200

        elif status in ['FAILED', 'PENDING']:
            customer_phone = None
            for phone, state in bot.user_states.items():
                if state.get('order_id') == order_id:
                    customer_phone = phone
                    break

            if customer_phone:
                whatsapp_phone = bot.format_phone_number(customer_phone)
                
                if status == 'FAILED':
                    message = f"""❌ Payment Failed

🔖 Order ID: {order_id}

Please try again or contact us:
📞 +91-9327256068"""
                else:
                    message = f"""⏳ Payment Pending

🔖 Order ID: {order_id}

Please complete the payment or contact:
📞 +91-9327256068"""

                bot.send_whatsapp_message(whatsapp_phone, message)

            return "Webhook received successfully", 200

        return "Webhook received successfully", 200

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


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


# Test endpoints
@app.route('/test/order', methods=['POST'])
def test_order():
    """Test order confirmation - Use this to test manually"""
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


@app.route('/test/payment', methods=['POST'])
def test_payment():
    """Test payment link creation - Use this to test payment gateway"""
    data = request.json or {}
    
    sample_order = {
        'name': data.get('name', 'Test Customer'),
        'phone': data.get('phone', '9876543210'),
        'foodItems': data.get('foodItems', 'Masala Dosa'),
        'total': data.get('total', 99)
    }
    
    print(f"\n🧪 Testing payment link creation...")
    result = bot.payment_gateway.create_payment_link(sample_order)
    
    if result and result.get('success'):
        return jsonify({
            'success': True,
            'payment_link': result['payment_link'],
            'order_id': result['order_id'],
            'amount': result['amount'],
            'message': 'Payment link created successfully!'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to create payment link',
            'possible_reasons': [
                'API key not set or invalid',
                'Network connection issue',
                'Pay0.shop service temporarily unavailable'
            ]
        }), 500


@app.route('/test/manual-payment', methods=['GET'])
def test_manual_payment():
    """Generate a manual payment link for testing"""
    print("\n🔧 Manual Payment Link Generator")
    print("="*70)
    
    # Sample data
    test_data = {
        'name': 'Manual Test',
        'phone': '9876543210',
        'foodItems': 'Test Item',
        'total': 99
    }
    
    result = bot.payment_gateway.create_payment_link(test_data)
    
    if result and result.get('success'):
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Payment Link</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #28a745;
                }}
                .info {{
                    margin: 20px 0;
                    padding: 15px;
                    background: #f8f9fa;
                    border-left: 4px solid #007bff;
                }}
                .btn {{
                    display: inline-block;
                    padding: 15px 30px;
                    background: #28a745;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin-top: 20px;
                }}
                .btn:hover {{
                    background: #218838;
                }}
                code {{
                    background: #f8f9fa;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Payment Link Generated!</h1>
                <div class="info">
                    <p><strong>Order ID:</strong> {result['order_id']}</p>
                    <p><strong>Amount:</strong> ₹{result['amount']}</p>
                    <p><strong>Customer:</strong> {test_data['name']}</p>
                    <p><strong>Phone:</strong> {test_data['phone']}</p>
                </div>
                <a href="{result['payment_link']}" class="btn" target="_blank">
                    💳 Open Payment Link
                </a>
                <div style="margin-top: 30px; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107;">
                    <p><strong>Payment URL:</strong></p>
                    <code style="word-break: break-all;">{result['payment_link']}</code>
                </div>
            </div>
        </body>
        </html>
        """
        return html_response
    else:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Link Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #dc3545;
                }}
                .error {{
                    margin: 20px 0;
                    padding: 15px;
                    background: #f8d7da;
                    border-left: 4px solid #dc3545;
                    color: #721c24;
                }}
                ul {{
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ Payment Link Error</h1>
                <div class="error">
                    <p><strong>Failed to generate payment link</strong></p>
                    <p>Possible reasons:</p>
                    <ul>
                        <li>PAYO_API_KEY not set in Variables.env</li>
                        <li>Invalid API key</li>
                        <li>Network connection issue</li>
                        <li>Pay0.shop service unavailable</li>
                    </ul>
                </div>
                <p>Check the server console logs for more details.</p>
            </div>
        </body>
        </html>
        """, 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'WhatsApp Order Bot with Pay0.shop',
        'endpoints': {
            'google_sheets': '/webhook/google-sheets',
            'whatsapp': '/webhook/whatsapp',
            'payo_callback': '/webhook/payo-callback',
            'test_order': '/test/order (POST)',
            'test_payment': '/test/payment (POST)',
            'test_manual_payment': '/test/manual-payment (GET)'
        },
        'payment_gateway': 'Pay0.shop',
        'config': {
            'base_url': PAYO_BASE_URL,
            'webhook_url': PAYO_WEBHOOK_URL,
            'api_key_set': bool(PAYO_USER_TOKEN),
            'whatsapp_configured': bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)
        }
    })


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🤖 WhatsApp Order Bot with Pay0.shop Payment Gateway")
    print("="*70)
    
    required_vars = {
        'WHATSAPP_TOKEN': WHATSAPP_TOKEN,
        'WHATSAPP_PHONE_ID': WHATSAPP_PHONE_ID,
        'PAYO_API_KEY': PAYO_USER_TOKEN,
        'WEBSITE_URL': WEBSITE_URL
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            if 'API_KEY' in var_name or 'TOKEN' in var_name:
                masked = '*' * 20 + (var_value[-8:] if len(var_value) > 8 else var_value[-4:])
                print(f"✅ {var_name}: {masked}")
            else:
                print(f"✅ {var_name}: {var_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            all_set = False
    
    print("\n💳 Payment Gateway Configuration:")
    print(f"   Provider: Pay0.shop")
    print(f"   Base URL: {PAYO_BASE_URL}")
    print(f"   Webhook: {PAYO_WEBHOOK_URL}")
    print(f"   API Key: {'Configured' if PAYO_USER_TOKEN else 'NOT SET'}")
    
    print("\n🔧 Test Endpoints:")
    print(f"   Manual Payment Link: http://localhost:5000/test/manual-payment")
    print(f"   Health Check: http://localhost:5000/health")
    
    if all_set:
        print("\n✅ All configurations set!")
        print("🚀 Bot is ready to accept orders!")
        print(f"🌐 Website: {WEBSITE_URL}")
        print("="*70 + "\n")
        app.run(debug=False, host='0.0.0.0', port=5000)
    else:
        print("\n❌ Please set missing variables in Variables.env")
        print("\n📝 Required in Variables.env:")
        print("   WHATSAPP_TOKEN=your_whatsapp_token")
        print("   WHATSAPP_PHONE_ID=your_phone_id")
        print("   PAYO_API_KEY=your_pay0_api_key")
        print("   WEBSITE_URL=your_website_url")
        print("="*70)