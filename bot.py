from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, LabeledPrice, Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import os, json, random
from kb import *
from models import session, Product

load_dotenv()

bot_token = os.getenv("bot_token")
stripe_token = os.getenv("stripe_token")
owners = json.loads(os.getenv("owners"))
bot = TeleBot(bot_token, parse_mode="HTML")

def productkb(i, cat):
    category = session.query(Category).get(cat).products
    fproduct, lproduct = category[0], category[-1]
    prod = session.query(Product).get(i)
    index = category.index(prod)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Buy", pay=True), InlineKeyboardButton("Add to cart🛒", callback_data=f"+cart{i}"))
    if i != fproduct.id:
        prev = InlineKeyboardButton("🔼 Previous", callback_data=f"cp{cat}:{category[index-1].id}")
        kb.add(prev)
    if i != lproduct.id:
        next_ = InlineKeyboardButton("🔽 Next", callback_data=f"cp{cat}:{category[index+1].id}")
        kb.add(next_)
    return kb


@bot.message_handler(["start"])
def start(message):
    bot.send_message(message.chat.id, "<b>Hello welcome to the store!!</b>", reply_markup=kb)

@bot.message_handler(["admin"], func=lambda message: message.chat.id in owners)
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

    if call.data.startswith("admin_") and message.chat.id in owners:
        data = call.data[6:]
        if data == "newproduct":
            bot.send_message(message.chat.id, "What is the name of product?")
            bot.register_next_step_handler(message, add_product)
        elif data in ["products", "prod_back"]:
            bot.edit_message_text("Select Product", message.chat.id, message.id, reply_markup=Admin.get_products())
        
        elif data in ["categories", "cat_back"]:
            bot.edit_message_text("Select a category", message.chat.id, message.id, reply_markup=Admin.get_categories())
        
        elif data == "home":
            bot.edit_message_text("<b>Hello Admin !</b> What will you like to edit today?", message.chat.id, message.id, reply_markup=Admin.keyboard)

        elif data.startswith("p") and data[1:].isdigit():
            product = session.query(Product).get(int(data[1:]))
            bot.edit_message_text(f"Edit Product\nName: {product.name}\nPrice: {product.price}\nDescription: {product.description}", message.chat.id, message.id, reply_markup=Admin.edit_product(data[1:]))

        elif data.startswith("editcat"):
            _, cat_id = data.split(":")
            category = session.query(Category).get(cat_id)
            bot.edit_message_text(f"Name: {category.name}", message.chat.id, message.id, reply_markup=Admin.edit_category(cat_id))

        elif data.startswith("e") and data[1] in ["n", "p", "d", "c", "i"]:
            product_id = data[3:]
            if data[1] == "c":
                bot.edit_message_text(f"Select the category you want to transfer the product to", message.chat.id, message.id, reply_markup=Admin.edit_product_category(product_id))
                return
            elif data[1] == "i":
                bot.edit_message_text(f"Send the image you want to use", message.chat.id, message.id, reply_markup=InlineKeyboardMarkup().add(Admin.back))
                bot.register_next_step_handler(message, edit_image, product_id)
                return
            n = {"n":"name", "p":"price", "d": "description"}
            bot.send_message(message.chat.id, f"Send the new {n[data[1]]}")
            bot.register_next_step_handler(message, edit_product, data[1], product_id)
        
        elif data.startswith("create_cat"):
            bot.send_message(message.chat.id, "What is the name of the category?")
            bot.register_next_step_handler(message, new_category)

        elif data.startswith("chancatname"):
            _, cat_id = data.split(":")
            bot.send_message(message.chat.id, f"What do you want to change the category name to?")
            bot.register_next_step_handler(message, change_category_name, cat_id)

        elif data.startswith("del"):
            _, prod_id = data.split(":")
            name = session.query(Product).get(int(prod_id)).name
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("✅Yes", callback_data=f"confirm_del:{prod_id}"), InlineKeyboardButton("❌ No", callback_data=f"admin_prod_back"))
            bot.edit_message_text("Are you sure you want to delete "+name.upper(), message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("confirm_del"):
            _, prod_id = data.split(":")
            prod = session.query(Product).get(int(prod_id))
            session.delete(prod)
            session.commit()
            kb = InlineKeyboardMarkup().add(Admin.back)
            bot.edit_message_text(prod.name+" has been deleted", message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("chan_cat"):
            _, prod_id, cat_id = data.split(":")
            product = session.query(Product).get(int(prod_id))
            product.category = cat_id
            session.commit()
            kb = InlineKeyboardMarkup().add(Admin.back)
            bot.edit_message_text(f"{product.name}'s category has been updated!", message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("nprod_cat"):
            _, prod_id, cat_id = data.split(":")
            session.query(Product).get(int(prod_id)).category = cat_id
            session.commit()
            bot.send_message(message.chat.id, "Product added successfully!!!", reply_markup=InlineKeyboardMarkup().add(Admin.back))

def new_category(message):
    if message.text:
        if is_cancel(message): return
        category = Category(name=message.text)
        session.add(category)
        session.commit()
        bot.send_message(message.chat.id, "Category created", reply_markup=InlineKeyboardMarkup().add(Admin.cat_back))
    else:
        bot.send_message(message.chat.id, "Please send a text message")
        bot.register_next_step_handler(message, new_category)

def change_category_name(message, cat_id):
    if message.text:
        if is_cancel(message): return
        category = session.query(Category).get(cat_id)
        category.name = message.text
        session.commit()
        bot.send_message(message.chat.id, "Category name modified to "+message.text, reply_markup=InlineKeyboardMarkup().add(Admin.cat_back))
    else:
        bot.send_message(message.chat.id, "Please send a text message")
        bot.register_next_step_handler(message, change_category_name)

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
    bot.send_message(message.chat.id, "Send the image for the product")
    bot.register_next_step_handler(message, add_image, details)

def random_string():
    return str(random.randint(1000, 9999))

def add_image(message:Message, details):
    if is_cancel(message): return
    details["image"] = message.photo[1].file_id
    product = Product(**details)
    session.add(product)
    session.commit()
    markup = InlineKeyboardMarkup()
    categories = session.query(Category).all()
    markup.add(*[InlineKeyboardButton(i.name, callback_data=f"admin_nprod_cat:{product.id}:{i.id}") for i in categories])
    bot.send_message(message.chat.id, "Select the category to add the product", reply_markup=markup)

def edit_product(message, pty, pid):
    product = session.query(Product).get(pid)
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

def edit_image(message, prod_id):
    if is_cancel(message): return
    p = session.query(Product).get(prod_id)
    p.image = message.photo[1].file_id
    session.commit()
    bot.send_message(message.chat.id, p+" Image has been replaced!", reply_markup=InlineKeyboardMarkup().add(Admin.back))

def is_cancel(message):
    if message.text in ["/start", "/cancel", "/admin"]:
        bot.send_message(message.chat.id, "Operation cancelled")
        bot.clear_step_handler(message)
        globals()[message.text[1:]](message)
        return True
    return False

def send_invoice(message:Message, product:Product, cat):
    bot.send_invoice(
        message.chat.id, product.name, product.description,
        "true", stripe_token, "usd", [LabeledPrice(product.name, int(product.price*100))], photo_url=bot.get_file_url(product.image) if product.image else None, reply_markup=productkb(product.id, cat))

bot.enable_save_next_step_handlers(1)
print("Started")
bot.infinity_polling()