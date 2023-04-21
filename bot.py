from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, LabeledPrice, Message
from dotenv import load_dotenv
import os

load_dotenv()

bot_token = os.getenv("bot_token")
stripe_token = os.getenv("stripe_token")
bot = TeleBot(bot_token, parse_mode="HTML")

desc = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
products = {
    "1": {"name": "Cooker", "price": 100, "desc": desc},
    "2": {"name": "Electric kettle", "price": 80, "desc": desc},
    "3": {"name": "Blender", "price": 60, "desc": desc}
}

categorykb = InlineKeyboardMarkup(row_width=2)
btn1 = InlineKeyboardButton("Category 1", callback_data="c1")
btn2 = InlineKeyboardButton("Category 2", callback_data="c2")
btn3 = InlineKeyboardButton("Category 3", callback_data="c3")
btn4 = InlineKeyboardButton("Category 4", callback_data="c4")
categorykb.add(btn1, btn2, btn3, btn4)


def Productkb(i):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Buy", pay=True), InlineKeyboardButton("Add to cart🛒", callback_data=f"+cart{i}"))
    if i != "1":
        prev = InlineKeyboardButton("🔼 Previous", callback_data=int(i)-1)
        kb.add(prev)
    if i != len(products):
        next_ = InlineKeyboardButton("🔽 Next", callback_data=int(i)+1)
        kb.add(next_)
    return kb


def get_product_details(product_details):
    return f"<b>{product_details['name']}</b>\nPrice: <b>${product_details['price']}</b>\nDescription: {desc}"


@bot.message_handler(["start"])
def start(message):
    bot.send_message(
        message.chat.id, "Hello welcome to the store.\n\nWhat category would you like to browse", reply_markup=categorykb)


@bot.callback_query_handler(func=lambda call: call.data != None)
def callback_handler(call: CallbackQuery):
    message = call.message

    if call.data.startswith("c"):
        call.data = call.data.strip("c")
        if call.data.isdigit():
            product_details = products["1"]
            send_invoice(message, product_details, "1")
    elif call.data.isdigit():
        product_details = products.get(call.data)
        bot.delete_message(message.chat.id, message.id)
        if not product_details:
            bot.send_message(call.message.chat.id, "Product is unavailable!☹️")
            return
        send_invoice(message, product_details, call.data)

def send_invoice(message:Message, product_details, prod_id):
    bot.send_invoice(
        message.chat.id, product_details['name'], product_details["desc"], 
        "true", stripe_token, "usd",
        [LabeledPrice(product_details['name'], product_details['price']*100)], reply_markup=Productkb(prod_id))

print("Started")
bot.infinity_polling()
