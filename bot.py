from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, LabeledPrice, Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import os
from kb import *
from models import session, Product

load_dotenv()

bot_token = os.getenv("bot_token")
stripe_token = os.getenv("stripe_token")
owner = int(os.getenv("owner"))
bot = TeleBot(bot_token, parse_mode="HTML")

def productkb(i, cat):
    products = session.query(Product).filter_by(category=cat).count()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Buy", pay=True), InlineKeyboardButton("Add to cart🛒", callback_data=f"+cart{i}"))
    if i != 1:
        prev = InlineKeyboardButton("🔼 Previous", callback_data=f"p{i-1}")
        kb.add(prev)
    if i != products:
        next_ = InlineKeyboardButton("🔽 Next", callback_data=f"p{i+1}")
        kb.add(next_)
    return kb


@bot.message_handler(["start"])
def start(message):
    bot.send_message(message.chat.id, "<b>Hello welcome to the store!!</b>", reply_markup=kb)

@bot.message_handler(["admin"], func=lambda message: message.chat.id == owner)
def admin(message):
    bot.send_message(message.chat.id, "<b>Hello Admin !</b> What will you like to edit today?", reply_markup=Admin.keyboard)

@bot.message_handler(func=lambda msg: msg.text != None)
def message_handler(message: Message):
    if message.text == "Prodotti":
        bot.send_message(message.chat.id, "What category would you like to browse?", reply_markup=Customer.get_categories())

@bot.callback_query_handler(func=lambda call: call.data != None)
def callback_handler(call: CallbackQuery):
    message = call.message

    if call.data.startswith("cp"):
        cat, prod = call.data.strip("cp").split(":")
        product = session.query(Product).filter_by(id=int(prod), category=int(cat)).first()
        bot.delete_message(message.chat.id, message.id)
        if not product:
            bot.send_message(message.chat.id, "Product is unavailable!☹️")
            return
        send_invoice(message, product, cat)

    if call.data.startswith("admin_") and message.chat.id == owner:
        data = call.data[6:]
        if data == "newproduct":
            bot.send_message(message.chat.id, "What is the name of product?")
            bot.register_next_step_handler(message, add_product)
        elif data in ["products", "prod_back"]:
            bot.edit_message_text("Select Product", message.chat.id, message.id, reply_markup=Admin.get_products())
        elif data.startswith("p") and data[1:].isdigit():
            product = session.query(Product).get(int(data[1:]))
            bot.edit_message_text(f"Edit Product\nName: {product.name}\nPrice: {product.price}\nDescription: {product.description}", message.chat.id, message.id, reply_markup=Admin.edit_product(data[1:]))
        elif data.startswith("e") and data[1] in ["n", "p", "d"]:
            product_id = data[3:]
            n = {"n":"name", "p":"price", "d": "description"}
            bot.send_message(message.chat.id, f"Send the new {n[data[1]]}")
            bot.register_next_step_handler(message, edit_product, data[1], product_id)

def add_product(message):
    if is_cancel(message): return
    bot.send_message(message.chat.id, "What price is it (in $) e.g 100, 200 e.t.c")
    details = {"name": message.text}
    bot.register_next_step_handler(message, add_price, details)

def add_price(message, details):
    if is_cancel(message): return
    try:
        details["price"] = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Only numbers allowed. Try again")
        bot.register_next_step_handler(message, add_price, details)
        return
    bot.send_message(message.chat.id, "What is the description?")
    bot.register_next_step_handler(message, add_desc, details)

def add_desc(message, details):
    if is_cancel(message): return
    details["description"] = message.text
    session.add(Product(**details, category=1))
    session.commit()
    bot.send_message(message.chat.id, "Product added successfully!!!")
    admin(message)

def edit_product(message, pty, pid):
    product = session.query(Product).get(pid)
    n = {"n":product.name, "p":product.price, "d": product.description}
    if pty == "n":
        product.name = message.text
    elif pty == "d":
        product.description = message.text
    elif pty == "p":
        try:
            product.price = float(message.text)
        except ValueError:
            bot.send_message(message.chat.id, "Only numbers allowed. Try again")            
            bot.register_next_step_handler(message, edit_product, pty, pid)
            return
    session.commit()
    bot.send_message(message.chat.id, "Product updated !!!")
    bot.send_message(message.chat.id, f"Edit Product\nName: {product.name}\nPrice: {product.price}\nDescription: {product.description}", reply_markup=Admin.edit_product(pid))

def is_cancel(message):
    if message.text in ["/start", "/cancel", "/admin"]:
        bot.send_message(message.chat.id, "Operation cancelled")
        bot.clear_step_handler(message)
        globals()[message.text[1:]]()
        return True
    return False

def send_invoice(message:Message, product:Product, cat):
    bot.send_invoice(
        message.chat.id, product.name, product.description,
        "true", stripe_token, "usd", [LabeledPrice(product.name, int(product.price*100))], reply_markup=productkb(product.id, cat))

# session.add(Category(name="category 1"))
# session.commit()
print("Started")
bot.infinity_polling()