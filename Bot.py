import telebot
import requests
import time
import threading
from telebot import types

# --- কনফিগারেশন ---
API_KEY = "nxa_2061f3a8e91e9f660d7934ebf8b89af4782bb5f6"
BASE_URL = "http://nexaotpservice.com/api/v1"
BOT_TOKEN = "8859654116:AAFar_PvwZ6MEBkf8klPe7FS1bPpAq1aVgc"
ADMIN_ID = 6941003064

HEADERS = {"X-API-Key": API_KEY}
bot = telebot.TeleBot(BOT_TOKEN)

# ডাটাবেজ স্ট্রাকচার
SERVICES_DATA = {}

# স্টেট ও সেশন ট্র্যাকিং
user_steps = {}
admin_temp_data = {}
active_user_sessions = {}  # {chat_id: current_number_id}

def is_admin(chat_id):
    return chat_id == ADMIN_ID

# ---------------------------------------------------------
# এডমিন প্যানেল
# ---------------------------------------------------------
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ আপনি এই বটের এডমিন নন।")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("➕ নতুন সার্ভিস তৈরি করুন", callback_data="adm_create_service")
    btn2 = types.InlineKeyboardButton("🌍 সার্ভিসে কান্ট্রি/রেঞ্জ যোগ করুন", callback_data="adm_add_country")
    btn3 = types.InlineKeyboardButton("🗑️ সার্ভিসের কান্ট্রি ডিলিট করুন", callback_data="adm_del_country_select")
    btn4 = types.InlineKeyboardButton("🛠️ মেইনটেইনেন্স মোড (অন/অফ)", callback_data="adm_toggle_maintenance")
    btn5 = types.InlineKeyboardButton("📋 বর্তমান লিস্ট ও স্ট্যাটাস দেখুন", callback_data="adm_view_all")
    btn6 = types.InlineKeyboardButton("🗑️ পুরো সার্ভিস ডিলিট করুন", callback_data="adm_delete_service")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    bot.send_message(message.chat.id, "⚙️ **SHxNumber Zone - এডমিন প্যানেল**", reply_markup=markup, parse_mode="Markdown")

# ---------------------------------------------------------
# ইউজার ইন্টারফেস
# ---------------------------------------------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = (
        "👋 **স্বাগতম SHxNumber Zone-এ!**\n\n"
        "🔥 এই বটের সমস্ত নাম্বার সম্পূর্ণ **ফ্রি**!\n"
        "💡 *Get number select service and country*\n\n"
        "নিচের বাটনে ক্লিক করে এখনই আপনার ফ্রি নাম্বার নিন।"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎁 ফ্রি নাম্বার নিন"))
    if is_admin(message.chat.id):
        markup.add(types.KeyboardButton("⚙️ এডমিন প্যানেল"))
        
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if text == "🎁 ফ্রি নাম্বার নিন":
        show_services(chat_id)
    elif text == "⚙️ এডমিন প্যানেল" and is_admin(chat_id):
        admin_panel(message)
    else:
        if chat_id in user_steps:
            step = user_steps[chat_id]
            
            if step == "waiting_new_service":
                srv_name = text.lower()
                if srv_name in SERVICES_DATA:
                    bot.send_message(chat_id, "❌ এই সার্ভিসটি অলরেডি আছে।")
                else:
                    SERVICES_DATA[srv_name] = {"status": "active", "countries": {}}
                    bot.send_message(chat_id, f"✅ সার্ভিস **{srv_name.upper()}** তৈরি হয়েছে। এবার কান্ট্রি ও রেঞ্জ এড করুন।", parse_mode="Markdown")
                del user_steps[chat_id]
            
            elif step == "waiting_country_code":
                admin_temp_data[chat_id]["country"] = text.upper()
                user_steps[chat_id] = "waiting_range"
                bot.send_message(chat_id, "📝 নাম্বারের নির্দিষ্ট **Range / Prefix** টি লিখুন (যেমন: `26138`, `88019`):")
                
            elif step == "waiting_range":
                srv = admin_temp_data[chat_id]["service"]
                cnt = admin_temp_data[chat_id]["country"]
                rng = text
                
                SERVICES_DATA[srv]["countries"][cnt] = {"range": rng}
                bot.send_message(chat_id, f"🎉 **সফলভাবে যুক্ত হয়েছে!**\n\n🎯 সার্ভিস: `{srv.upper()}`\n🌍 কান্ট্রি: `{cnt}`\n🔢 রেঞ্জ: `{rng}`", parse_mode="Markdown")
                del user_steps[chat_id]
                del admin_temp_data[chat_id]

def show_services(chat_id):
    if not SERVICES_DATA:
        bot.send_message(chat_id, "❌ এই মুহূর্তে কোনো সার্ভিস উপলব্ধ নেই।")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for srv, info in SERVICES_DATA.items():
        status_label = " [🛠️ Maintenance]" if info["status"] == "maintenance" else ""
        markup.add(types.InlineKeyboardButton(f"{srv.upper()}{status_label}", callback_data=f"usr_select_{srv}"))
        
    bot.send_message(chat_id, "🎯 **কোন সার্ভিসের ফ্রি নাম্বার চান? সিলেক্ট করুন:**", reply_markup=markup, parse_mode="Markdown")

def show_countries(chat_id, service):
    srv_info = SERVICES_DATA.get(service)
    if srv_info["status"] == "maintenance":
        bot.send_message(chat_id, f"❌ দুঃখিত, **{service.upper()}** সার্ভিসটি বর্তমানে মেইনটেইনেন্সে আছে।", parse_mode="Markdown")
        return

    countries = srv_info.get("countries", {})
    if not countries:
        bot.send_message(chat_id, "❌ এই সার্ভিসের অধীনে কোনো কান্ট্রি সেট করা নেই।")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    for cnt in countries.keys():
        markup.add(types.InlineKeyboardButton(f"🌍 {cnt}", callback_data=f"getfree_{service}_{cnt}"))
        
    bot.send_message(chat_id, f"⚡ **{service.upper()}**-এর জন্য কান্ট্রি সিলেক্ট করুন:", reply_markup=markup, parse_mode="Markdown")

# ---------------------------------------------------------
# 🎯 ওটিপি পোলিং সিস্টেম (ডাইনামিক number_id ভিত্তিক)
# ---------------------------------------------------------
def poll_for_otp(chat_id, number_id, number):
    # কারেন্ট ইউজারের সেশনে এই নির্দিষ্ট আইডিটি সেট করে দেওয়া হলো
    active_user_sessions[chat_id] = number_id
    
    # ৬০ বার ট্রাই করবে (২ সেকেন্ড পর পর = ১২০ সেকেন্ড)
    for _ in range(60):
        # ইউজার যদি রিফ্রেশ বাটনে ক্লিক করে নতুন নাম্বারের জন্য রিকোয়েস্ট দেয়, 
        # তবে সেশনের আইডি বদলে যাবে এবং এই আগের লুপটি সাথে সাথে বন্ধ হয়ে যাবে।
        if active_user_sessions.get(chat_id) != number_id:
            print(f"[POLLING] Stopped old polling for user {chat_id} on number {number}")
            return

        url = f"{BASE_URL}/numbers/{number_id}/sms"
        
        try:
            response_raw = requests.get(url, headers=HEADERS, timeout=8)
            response = response_raw.json()
            
            # টার্মিনাল লগিং (ডিবাগ করার জন্য)
            print("Polling URL:", url)
            print("Response:", response)
            
            if response and response.get("success") is True:
                sms_data = response.get("sms")
                
                if isinstance(sms_data, list) and len(sms_data) > 0:
                    for item in sms_data:
                        otp_code = item.get("otp")
                        full_message = item.get("text") or item.get("message") or "মেসেজ টেক্সট পাওয়া যায়নি"
                        
                        if otp_code:
                            send_otp_success(chat_id, number, otp_code, full_message)
                            return
                            
                elif isinstance(sms_data, dict):
                    otp_code = sms_data.get("otp")
                    full_message = sms_data.get("text") or sms_data.get("message") or "মেসেজ টেক্সট পাওয়া যায়নি"
                    
                    if otp_code:
                        send_otp_success(chat_id, number, otp_code, full_message)
                        return
        except Exception as e:
            print(f"[ERROR] Polling loop exception: {e}")
            pass
            
        time.sleep(2)
    
    if active_user_sessions.get(chat_id) == number_id:
        bot.send_message(chat_id, f"❌ `{number}` নাম্বারে সময়মতো ওটিপি আসেনি।\n💡 *Get number select service and country*", parse_mode="Markdown")

def send_otp_success(chat_id, number, otp_code, full_message):
    success_text = (
        "🎉 **নতুন OTP এসেছে!**\n\n"
        f"📱 **নাম্বার:** `{number}`\n"
        f"🔑 **OTP:** `{otp_code}`\n\n"
        f"💬 **সম্পূর্ণ মেসেজ:**\n`{full_message}`"
    )
    bot.send_message(chat_id, success_text, parse_mode="Markdown")

def request_and_process_number(chat_id, service, country):
    status_msg = bot.send_message(chat_id, "🔄 আপনার জন্য নতুন ফ্রি নাম্বার তোলা হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")
    
    try:
        range_prefix = SERVICES_DATA[service]["countries"][country]["range"]
        
        # ডক অনুযায়ী ক্লিয়ার পেলোড (ইঞ্জিন ১ সহ)
        req_data = {
            "service": service, 
            "country": country,
            "range": range_prefix,
            "engine": 1
        }
        r = requests.post(f"{BASE_URL}/numbers/get", headers=HEADERS, json=req_data, timeout=10).json()
        
        if r and r.get("success") is True:
            number = r["number"]
            number_id = r["number_id"] # এখানে এপিআই থেকে আসা রিয়েল-টাইম ইউনিক আইডি রিসিভ হচ্ছে
            
            markup = types.InlineKeyboardMarkup()
            refresh_btn = types.InlineKeyboardButton("🔄 Refresh / New Number", callback_data=f"refresh_{service}_{country}")
            markup.add(refresh_btn)
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"✅ **নাম্বার রেডি!**\n🔢 **নাম্বার:** `{number}`\n\n⏳ বটের ব্যাকগ্রাউন্ডে ওটিপি চেক করা হচ্ছে (সর্বোচ্চ ১২০ সেকেন্ড)...",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            
            # প্রাপ্ত ডাইনামিক number_id টিকেই পোলিংয়ে পাস করা হলো
            t = threading.Thread(target=poll_for_otp, args=(chat_id, number_id, number))
            t.daemon = True
            t.start()
        else:
            error_msg = r.get("message", "নাম্বার স্টক আউট বা এপিআই ব্যালেন্স শেষ।")
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"❌ নাম্বার পাওয়া যায়নি।\n**কারণ:** {error_msg}\n💡 *Get number select service and country*")
    except:
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="❌ API সার্ভার রেসপন্স করছে না।")

# ---------------------------------------------------------
# বাটন ক্লিক ইভেন্ট হ্যান্ডলার
# ---------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

    # --- এডমিন অ্যাকশনসমূহ ---
    if data == "adm_create_service" and is_admin(chat_id):
        user_steps[chat_id] = "waiting_new_service"
        bot.send_message(chat_id, "📝 নতুন সার্ভিসের নাম লিখুন (যেমন: `google`, `telegram`):")
        
    elif data == "adm_add_country" and is_admin(chat_id):
        if not SERVICES_DATA:
            bot.send_message(chat_id, "❌ আগে একটি সার্ভিস তৈরি করুন।")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        for srv in SERVICES_DATA.keys():
            markup.add(types.InlineKeyboardButton(srv.upper(), callback_data=f"adm_addcnt_{srv}"))
        bot.send_message(chat_id, "🎯 কোন সার্ভিসে কান্ট্রি যোগ করতে চান? সিলেক্ট করুন:", reply_markup=markup)
        
    elif data.startswith("adm_addcnt_") and is_admin(chat_id):
        selected_srv = data.replace("adm_addcnt_", "")
        admin_temp_data[chat_id] = {"service": selected_srv}
        user_steps[chat_id] = "waiting_country_code"
        bot.send_message(chat_id, f"📝 **{selected_srv.upper()}** এর জন্য কান্ট্রি কোড দিন (যেমন: `BD`, `MG`):")

    elif data == "adm_del_country_select" and is_admin(chat_id):
        if not SERVICES_DATA:
            bot.send_message(chat_id, "❌ কোনো সার্ভিস উপলব্ধ নেই।")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        for srv in SERVICES_DATA.keys():
            markup.add(types.InlineKeyboardButton(srv.upper(), callback_data=f"admdelsrv_{srv}"))
        bot.send_message(chat_id, "🗑️ কোন সার্ভিসের কান্ট্রি ডিলিট করতে চান? সার্ভিসটি সিলেক্ট করুন:", reply_markup=markup)

    elif data.startswith("admdelsrv_") and is_admin(chat_id):
        srv = data.replace("admdelsrv_", "")
        countries = SERVICES_DATA.get(srv, {}).get("countries", {})
        if not countries:
            bot.send_message(chat_id, f"❌ **{srv.upper()}** সার্ভিসের ভেতরে কোনো কান্ট্রি নেই।")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cnt in countries.keys():
            markup.add(types.InlineKeyboardButton(f"🌍 {cnt}", callback_data=f"forcedelcnt_{srv}_{cnt}"))
        bot.send_message(chat_id, f"🗑️ **{srv.upper()}** থেকে কোন কান্ট্রিটি ডিলিট করতে চান?", reply_markup=markup)

    elif data.startswith("forcedelcnt_") and is_admin(chat_id):
        parts = data.replace("forcedelcnt_", "").split("_")
        srv = parts[0]
        cnt = parts[1]
        if srv in SERVICES_DATA and cnt in SERVICES_DATA[srv]["countries"]:
            del SERVICES_DATA[srv]["countries"][cnt]
            bot.send_message(chat_id, f"✅ **{srv.upper()}** সার্ভিস থেকে কান্ট্রি **{cnt}** সফলভাবে ডিলিট করা হয়েছে।")

    elif data == "adm_toggle_maintenance" and is_admin(chat_id):
        if not SERVICES_DATA:
            bot.send_message(chat_id, "❌ কোনো সার্ভিস নেই।")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        for srv, info in SERVICES_DATA.items():
            current_status = "🛠️" if info["status"] == "maintenance" else "✅"
            markup.add(types.InlineKeyboardButton(f"{srv.upper()} ({current_status})", callback_data=f"maint_{srv}"))
        bot.send_message(chat_id, "🔧 মেইনটেইনেন্স অন/অফ করতে সার্ভিসের ওপর ক্লিক করুন:", reply_markup=markup)

    elif data.startswith("maint_") and is_admin(chat_id):
        srv = data.replace("maint_", "")
        if srv in SERVICES_DATA:
            new_status = "active" if SERVICES_DATA[srv]["status"] == "maintenance" else "maintenance"
            SERVICES_DATA[srv]["status"] = new_status
            bot.send_message(chat_id, f"📢 **{srv.upper()}** সার্ভিসটির স্ট্যাটাস পরিবর্তন করে **{new_status.upper()}** করা হয়েছে।")

    elif data == "adm_view_all" and is_admin(chat_id):
        if not SERVICES_DATA:
            bot.send_message(chat_id, "📋 কোনো ডাটা নেই।")
            return
        text = "📋 **বর্তমান বট কনফিগারেশন:**\n\n"
        for srv, info in SERVICES_DATA.items():
            text += f"🔸 **{srv.upper()}** [স্ট্যাটাস: {info['status'].upper()}]\n"
            for cnt, cnt_info in info["countries"].items():
                text += f"   ├── 🌍 কান্ট্রি: `{cnt}` | রেঞ্জ: `{cnt_info['range']}`\n"
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif data == "adm_delete_service" and is_admin(chat_id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        for srv in SERVICES_DATA.keys():
            markup.add(types.InlineKeyboardButton(f"🗑️ {srv.upper()}", callback_data=f"forcedel_{srv}"))
        bot.send_message(chat_id, "🗑️ কোন সার্ভিসটি সম্পূর্ণ ডিলিট করবেন?", reply_markup=markup)

    elif data.startswith("forcedel_") and is_admin(chat_id):
        srv = data.replace("forcedel_", "")
        if srv in SERVICES_DATA:
            del SERVICES_DATA[srv]
            bot.send_message(chat_id, f"✅ সার্ভিস **{srv.upper()}** সম্পূর্ণ ডিলিট হয়েছে।")

    # --- ইউজার অ্যাকশনসমূহ ---
    elif data.startswith("usr_select_"):
        selected_service = data.replace("usr_select_", "")
        show_countries(chat_id, selected_service)
        
    elif data.startswith("getfree_"):
        parts = data.replace("getfree_", "").split("_")
        service = parts[0]
        country = parts[1]
        request_and_process_number(chat_id, service, country)

    elif data.startswith("refresh_"):
        parts = data.replace("refresh_", "").split("_")
        service = parts[0]
        country = parts[1]
        request_and_process_number(chat_id, service, country)

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

# ---------------------------------------------------------
# 🚀 রানার
# ---------------------------------------------------------
if __name__ == "__main__":
    print("SHxNumber Zone Bot is strictly running on dynamic API response mapping...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(3)
