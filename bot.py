import telebot
import time
import requests
import threading
import random
import traceback
import os  # ✅ for environment variables

# ============ CONFIG ============
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")  # <-- Token ko env variable se read kare
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003892427527"))  # optional hide
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts="

# 🎯 STICKERS
WIN_STICKER_1 = "CAACAgUAAxkBAAFDlppppT351aarhWh_TG_tUy7uko-n6QACZRYAAqYtOVXs-2XdGTALsDoE"
WIN_STICKER_2 = "CAACAgUAAxkBAAFDlpxppT4FFNkF13KJ8AuYgZD4z7HWpAACWhoAAiWkMFXi4IKHogJcszoE"
LOSS_STICKER = "CAACAgUAAxkBAAFDlqJppT4bXj3NuDu4BZ6pSSVG_N8qcgACHhoAAsCAWFdNIjQkeNqKlzoE"

bot = telebot.TeleBot(BOT_TOKEN)

# ========= GLOBAL =========
last_finished_period = None
predictions = {}
win_count = 0
loss_count = 0
consec_loss_count = 0
winning_periods = []
all_results = []
session_number = 1

# ========= ADMIN PANEL =========
ADMIN_IDS = [6411315434]  # <-- apna telegram ID yaha daal
promo_text = """🚀 DM WIN Biggest Bonus Loot 🚀
... your promo text ...
"""
admin_waiting_for_promo = {}

@bot.message_handler(commands=['editpromo'])
def edit_promo_start(message):
    if message.from_user.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "📌 Send me the new promo message text:")
        admin_waiting_for_promo[message.from_user.id] = True
    else:
        bot.send_message(message.chat.id, "❌ You are not authorized to edit the promo message.")

@bot.message_handler(func=lambda m: admin_waiting_for_promo.get(m.from_user.id, False))
def receive_new_promo(message):
    global promo_text
    promo_text = message.text
    bot.send_message(message.chat.id, "✅ Promo message updated successfully!")
    admin_waiting_for_promo[message.from_user.id] = False

def promo_message():
    return promo_text

# ========= FUNCTIONS =========
def get_api():
    try:
        url = API_URL + str(int(time.time()*1000))
        return requests.get(url, timeout=10).json()
    except:
        return None

def number_to_bs(n):
    return "BIG" if int(n) >= 5 else "SMALL"

def ai_predict(history):
    last_numbers = [int(x["number"]) for x in history[:5]]
    trend = ["BIG" if n >= 5 else "SMALL" for n in last_numbers]

    if trend.count(trend[0]) == len(trend):
        return "SMALL" if trend[0] == "BIG" else "BIG"

    last = trend[0]
    if random.random() > 0.5:
        return "SMALL" if last == "BIG" else "BIG"
    else:
        return random.choice(["BIG", "SMALL"])

# ========= MAIN LOOP =========
def signal_loop():
    global last_finished_period, win_count, loss_count, consec_loss_count, winning_periods, session_number, all_results

    try:
        while True:
            data = get_api()
            if not data:
                time.sleep(2)
                continue

            history = data["data"]["list"]
            latest = history[0]

            finished = latest["issueNumber"]
            number = latest["number"]

            # RESULT CHECK
            if finished in predictions:
                pred = predictions.pop(finished)
                actual = number_to_bs(number)

                result_text = f"🧾 Period: {finished}\n📊 Prediction: {pred}\n📉 Result: {actual}"

                if pred == actual:
                    win_count += 1
                    consec_loss_count = 0
                    winning_periods.append(finished)
                    all_results.append({"period": finished, "prediction": pred, "result": actual, "status": "WIN"})

                    bot.send_message(CHANNEL_ID, f"🏆🔥 WIN CONFIRMED 🔥🏆\n\n{result_text}\n✨ Keep the streak going! ✨")
                    bot.send_sticker(CHANNEL_ID, WIN_STICKER_1)
                    bot.send_sticker(CHANNEL_ID, WIN_STICKER_2)
                else:
                    loss_count += 1
                    consec_loss_count += 1
                    all_results.append({"period": finished, "prediction": pred, "result": actual, "status": "LOSS"})
                    bot.send_message(CHANNEL_ID, f"❌ LOSS ❌\n\n{result_text}\n💔 Better luck next! 💔")
                    bot.send_sticker(CHANNEL_ID, LOSS_STICKER)

            # STOP AFTER 3 WINS
            if win_count >= 3:
                win_rate = (win_count / (win_count + loss_count)) * 100 if (win_count + loss_count) > 0 else 0
                stats_text = f"📊🔥 SESSION {session_number} WINNING PERIODS 🔥📊\n\n"
                for i, p in enumerate(winning_periods, 1):
                    stats_text += f"✨ #{i} ➤ {p} ✅💚\n"
                stats_text += f"\n🎯 TOTAL WINS: {win_count}\n❌ TOTAL LOSSES: {loss_count}\n📈 WIN RATE: {win_rate:.2f}%\n"
                small_count = sum(1 for r in all_results if r['result'] == 'SMALL')
                big_count = sum(1 for r in all_results if r['result'] == 'BIG')
                stats_text += f"🔹 SMALL: {small_count} | 🔸 BIG: {big_count}"

                bot.send_message(CHANNEL_ID, stats_text)
                bot.send_message(CHANNEL_ID, "📢 SESSION CLOSED 🚫\n\nNext session starting soon ⏳🔥")
                bot.send_message(CHANNEL_ID, promo_message())

                # RESET
                win_count = 0
                loss_count = 0
                consec_loss_count = 0
                winning_periods = []
                all_results = []
                session_number += 1
                time.sleep(10)
                continue

            # STOP AFTER 3 CONSECUTIVE LOSSES
            if consec_loss_count >= 3:
                bot.send_message(CHANNEL_ID, "⚠️ Session closed due to unstable results 📉\nPlease wait for next session ⏳")
                # RESET
                win_count = 0
                loss_count = 0
                consec_loss_count = 0
                winning_periods = []
                all_results = []
                session_number += 1
                time.sleep(10)
                continue

            # NEW SIGNAL
            if finished != last_finished_period:
                last_finished_period = finished
                next_period = str(int(finished) + 1)
                signal = ai_predict(history)
                predictions[next_period] = signal

                bot.send_message(
                    CHANNEL_ID,
                    f"🎯🔥 LIVE PREDICTION 🔥🎯\n\n⏭ Next Period: {next_period}\n📊 Signal: {signal}\n"
                    f"🔹 SMALL count: {sum(1 for r in all_results if r['result']=='SMALL')} | 🔸 BIG count: {sum(1 for r in all_results if r['result']=='BIG')}"
                )

            time.sleep(2)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"🚨 BOT CRASHED: {e}\n{error_trace}")
        try:
            bot.send_message(CHANNEL_ID, "⚠️ Auto Prediction Bot Stopped Due To Server Issue! ⚠️")
        except:
            pass
        time.sleep(10)
        signal_loop()  # auto-restart

# ========= START =========
threading.Thread(target=signal_loop, daemon=True).start()
print("🚀 24/7 BOT RUNNING...")
bot.infinity_polling()
