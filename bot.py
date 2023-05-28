from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, LabeledPrice, Message
from dotenv import load_dotenv
import os
import json
import random
from imgbb import ImgBB
from kb import *
from models import session, Product, Cart, Cartproduct, Order, Orderproduct

load_dotenv()

bot_token = os.getenv("bot_token")
stripe_token = os.getenv("stripe_token")
owners = json.loads(os.getenv("owners"))
bot = TeleBot(bot_token, parse_mode="HTML")
active = True

def productkb(i, cat):
    category = session.query(Category).get(cat).products
    fproduct, lproduct = category[0], category[-1]
    prod = session.query(Product).get(i)
    index = category.index(prod)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Buy", pay=True), InlineKeyboardButton(
        "🛒Add to cart", callback_data=f"+cart{i}"))
    if i != fproduct.id:
        prev = InlineKeyboardButton(
            "🔼 Previous", callback_data=f"cp{cat}:{category[index-1].id}")
        kb.add(prev)
    if i != lproduct.id:
        next_ = InlineKeyboardButton(
            "🔽 Next", callback_data=f"cp{cat}:{category[index+1].id}")
        kb.add(next_)
    return kb

def set_active(v):
    global active
    active = v
    return v


@bot.message_handler(["start"])
def start(message):
    if not active:
        bot.send_message(message.chat.id, "Bot 🤖 is not active now. Please try again later!")
        return
    bot.send_message(
        message.chat.id, "<b>Hello welcome to the store!!</b>", reply_markup=kb)


@bot.message_handler(["admin"], func=lambda message: message.chat.id in owners)
def admin(message):
    bot.send_message(
        message.chat.id, "<b>Hello Admin !</b> What will you like to edit today?", reply_markup=Admin.get_keyboard(active))

@bot.message_handler(["cart"])
def view_cart(message):
    if not active:
        bot.send_message(message.chat.id, "Bot 🤖 is not active now. Please try again later!")
        return
    kb = InlineKeyboardMarkup(row_width=2)
    user = session.query(Cart).get(message.chat.id)
    if not user or len(user.products) <= 0:
        bot.send_message(
            message.chat.id, "Your cart is empty!\n\nClick /products to browse")
        return
    for p in user.products:
        prod = session.query(Product).get(p.product_id)
        kb.add(InlineKeyboardButton(prod.name, callback_data=f"{prod.id}"), InlineKeyboardButton(
            "🗑️ Remove", callback_data=f"-cart:{prod.id}"))
    kb.add(InlineKeyboardButton("Checkout", callback_data="checkout"))
    bot.send_message(message.chat.id, "<b>Cart !</b>", reply_markup=kb)


@bot.message_handler(["products"])
def list_products(message):
    if not active:
        bot.send_message(message.chat.id, "Bot 🤖 is not active now. Please try again later!")
        return
    bot.send_message(message.chat.id, "What category would you like to browse?",
                     reply_markup=Customer.get_categories())


@bot.message_handler(func=lambda msg: msg.text != None)
def message_handler(message: Message):
    if not active:
        bot.send_message(message.chat.id, "Bot 🤖 is not active now. Please try again later!")
        return
    if message.text == "Prodotti":
        list_products(message)
    if message.text == "Cart":
        view_cart(message)


@bot.callback_query_handler(func=lambda call: call.data != None)
def callback_handler(call: CallbackQuery):
    message = call.message

    if not call.data.startswith("admin_") and not active:
        bot.send_message(message.chat.id, "Bot 🤖 is not active now. Please try again later!")
        return

    if call.data.startswith("cp"):
        cat, prod = call.data.strip("cp").split(":")
        product = session.query(Product).filter_by(
            id=int(prod), category=int(cat)).first()
        bot.delete_message(message.chat.id, message.id)
        if not product:
            bot.send_message(message.chat.id, "Product is unavailable!☹️")
            return
        send_invoice(message, product, cat)

    elif call.data.startswith("+cart"):
        prod_id = call.data[5:]
        user = get_user(message.chat.id)
        session.add(Cartproduct(product_id=int(prod_id), cart=user.id))
        session.commit()
        bot.answer_callback_query(call.id, f"Added to cart✅", True)

    elif call.data.startswith("-cart"):
        _, prod_id = call.data.split(":")
        user = get_user(message.chat.id)
        c = session.query(Cartproduct).filter(
            Cartproduct.product_id == prod_id, Cartproduct.cart == user.id).first()
        if c:
            session.delete(c)
            session.commit()
        total = 0
        kb = InlineKeyboardMarkup()
        for p in user.products:
            prod = session.query(Product).get(p.product_id)
            total += prod.price
            kb.add(InlineKeyboardButton(prod.name, callback_data=f"{prod.id}"), InlineKeyboardButton(
                "🗑️ Remove", callback_data=f"-cart:{prod.id}"))
        kb.add(InlineKeyboardButton("Checkout", callback_data=f"checkout"))
        bot.edit_message_text(
            f"Total: €{total}", message.chat.id, message.id, reply_markup=kb)

    elif call.data == "checkout":
        prices = []
        text = []
        user = get_user(message.chat.id)
        total = 0
        discount = 0
        for p in user.products:
            prod = session.query(Product).get(p.product_id)
            prices.append(LabeledPrice(prod.name, int(prod.price*100)))
            if prod.discount:
                discount += prod.price*prod.discount
            text.append(f"{prod.name} - €{prod.price}")
            total += prod.price
        shipping_cost = 6.5 if total < 49.99 else 0
        prices.append(LabeledPrice("Discount", -int(discount)))
        prices.append(LabeledPrice("Shipping", int(shipping_cost*100)))
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Pay", pay=True))
        bot.send_invoice(message.chat.id, "Your Order", ", ".join(text), "cart", stripe_token, "eur", prices,
                         need_email=True, need_shipping_address=True, send_email_to_provider=True, reply_markup=kb)

    if call.data.startswith("admin_") and message.chat.id in owners:
        data = call.data[6:]
        if data == "toggle_active":
            a = set_active(not active)
            bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup=Admin.get_keyboard(a))

        if data == "newproduct":
            bot.send_message(message.chat.id, "What is the name of product?")
            bot.register_next_step_handler(message, add_product)
        elif data in ["products", "prod_back"]:
            bot.clear_step_handler(message)
            bot.edit_message_text(
                "Select Product", message.chat.id, message.id, reply_markup=Admin.get_products())

        elif data in ["categories", "cat_back"]:
            bot.clear_step_handler(message)
            bot.edit_message_text("Select a category", message.chat.id,
                                  message.id, reply_markup=Admin.get_categories())

        elif data == "home":
            bot.edit_message_text("<b>Hello Admin !</b> What will you like to edit today?",
                                  message.chat.id, message.id, reply_markup=Admin.get_keyboard(active))

        elif data.startswith("p") and data[1:].isdigit():
            product = session.query(Product).get(int(data[1:]))
            if product.discount != 0 and product.discount:
                price_text = f"<s>${product.price}</s> ${product.price-(product.discount*product.price/100)} (-{product.discount}%)"
            else:
                price_text = f"${product.price} (No discount)"
            bot.edit_message_text(f"Edit Product\nName: {product.name}\nPrice: {price_text}\nDescription: {product.description}",
                                  message.chat.id, message.id, parse_mode="HTML", reply_markup=Admin.edit_product(data[1:]))

        elif data.startswith("editcat"):
            _, cat_id = data.split(":")
            category = session.query(Category).get(cat_id)
            bot.edit_message_text(f"Name: {category.name}", message.chat.id,
                                  message.id, reply_markup=Admin.edit_category(cat_id))

        elif data.startswith("e") and data[1] in ["n", "p", "d", "c", "i"]:
            product_id = data[3:]
            if data[1] == "c":
                bot.edit_message_text(f"Select the category you want to transfer the product to",
                                      message.chat.id, message.id, reply_markup=Admin.edit_product_category(product_id))
                return
            elif data[1] == "i":
                bot.edit_message_text(f"Send the image you want to use", message.chat.id,
                                      message.id, reply_markup=InlineKeyboardMarkup().add(Admin.back))
                bot.register_next_step_handler(message, edit_image, product_id)
                return
            elif data.split("_")[0] == "ediscount":
                prop = "discount"
                product_id = data.split("_")[-1]
            else:
                prop = data[1]
            n = {"n": "name", "p": "price", "d": "description", "discount": "discount (%)"}
            bot.send_message(message.chat.id, f"Send the new {n[prop]}")
            bot.register_next_step_handler(message, edit_product, prop, product_id)

        elif data.startswith("create_cat"):
            bot.send_message(
                message.chat.id, "What is the name of the category?")
            bot.register_next_step_handler(message, new_category)

        elif data.startswith("chancatname"):
            _, cat_id = data.split(":")
            bot.send_message(
                message.chat.id, f"What do you want to change the category name to?")
            bot.register_next_step_handler(
                message, change_category_name, cat_id)

        elif data.startswith("del"):
            _, prod_id = data.split(":")
            name = session.query(Product).get(int(prod_id)).name
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("✅Yes", callback_data=f"admin_confirm_del:{prod_id}"), InlineKeyboardButton(
                "❌ No", callback_data=f"admin_prod_back"))
            bot.edit_message_text("Are you sure you want to delete " +
                                  name.upper(), message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("confirm_del"):
            _, prod_id = data.split(":")
            prod = session.query(Product).get(int(prod_id))
            session.delete(prod)
            session.commit()
            kb = InlineKeyboardMarkup().add(Admin.back)
            bot.edit_message_text(
                prod.name+" has been deleted", message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("chan_cat"):
            _, prod_id, cat_id = data.split(":")
            product = session.query(Product).get(int(prod_id))
            product.category = cat_id
            session.commit()
            kb = InlineKeyboardMarkup().add(Admin.back)
            bot.edit_message_text(f"{product.name}'s category has been updated!",
                                  message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("nprod_cat"):
            _, prod_id, cat_id = data.split(":")
            session.query(Product).get(int(prod_id)).category = cat_id
            session.commit()
            bot.send_message(message.chat.id, "Product added successfully!!!",
                             reply_markup=InlineKeyboardMarkup().add(Admin.back))

        elif data == "view_orders":
            bot.edit_message_text(
                "Please choose", message.chat.id, message.id, reply_markup=Admin.view_orders_kb)

        elif data in ["pending_orders", "shipped_orders"]:
            pending_orders = session.query(Order).filter_by(
                shipped=data != "pending_orders").all()
            kb = InlineKeyboardMarkup()
            kb.add(*[InlineKeyboardButton("@"+order.username,
                   callback_data=f"admin_order_details:{order.id}") for order in pending_orders])
            kb.add(InlineKeyboardButton(
                "Back", callback_data="admin_view_orders"))
            bot.edit_message_text("Here are all the individuals with pending orders",
                                  message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("order_details"):
            _, orderid = data.split(":")
            order_details = session.query(Order).get(orderid)
            products = ""
            for i in order_details.products:
                products += f"<b>{i.name}</b>\n"
            kb = InlineKeyboardMarkup()
            if not order_details.shipped:
                kb.add(InlineKeyboardButton("Mark as Shipped", callback_data="admin_mark_shipped:"+str(orderid)))
            kb.add(Admin.pending_order_back if not order_details.shipped else Admin.shipping_order_back)
            bot.edit_message_text(f"Username: @{bot.get_chat(order_details.userid).username}\nShipping: {'Shipped' if order_details.shipped else 'Not shipped'}\n\nProducts\n{products}\n{order_details.shipping_address}", message.chat.id,
                                  message.id, reply_markup=kb)

        elif data.startswith("mark_shipped"):
            _, orderid = data.split(":")
            order = session.query(Order).get(orderid)
            order.shipped = True
            session.commit()
            bot.edit_message_text("Order marked as Shipped✅", message.chat.id, message.id,
                                  reply_markup=InlineKeyboardMarkup().add(Admin.pending_order_back))


def new_category(message):
    if message.text:
        if is_cancel(message):
            return
        category = Category(name=message.text)
        session.add(category)
        session.commit()
        bot.send_message(message.chat.id, "Category created",
                         reply_markup=InlineKeyboardMarkup().add(Admin.cat_back))
    else:
        bot.send_message(message.chat.id, "Please send a text message")
        bot.register_next_step_handler(message, new_category)


def change_category_name(message, cat_id):
    if message.text:
        if is_cancel(message):
            return
        category = session.query(Category).get(cat_id)
        category.name = message.text
        session.commit()
        bot.send_message(message.chat.id, "Category name modified to " +
                         message.text, reply_markup=InlineKeyboardMarkup().add(Admin.cat_back))
    else:
        bot.send_message(message.chat.id, "Please send a text message")
        bot.register_next_step_handler(message, change_category_name)


def add_product(message):
    if is_cancel(message):
        return
    bot.send_message(
        message.chat.id, "What price is it (in €) e.g 100, 200 e.t.c")
    details = {"name": message.text}
    bot.register_next_step_handler(message, add_price, details)


def add_price(message, details):
    if is_cancel(message):
        return
    try:
        details["price"] = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Only numbers allowed. Try again")
        bot.register_next_step_handler(message, add_price, details)
        return
    bot.send_message(message.chat.id, "What is the description?")
    bot.register_next_step_handler(message, add_desc, details)


def add_desc(message, details):
    if is_cancel(message):
        return
    details["description"] = message.text
    bot.send_message(message.chat.id, "Send the image for the product")
    bot.register_next_step_handler(message, add_image, details)


def random_string():
    return str(random.randint(1000, 9999))


def add_image(message: Message, details):
    if is_cancel(message):
        return
    if not message.document:
        bot.send_message(message.chat.id, "Please send the image as a file")
        bot.register_next_step_handler(message, add_image, details)
        return
    res = ImgBB.upload_file(bot.get_file_url(message.document.file_id))
    details["image"] = res["data"]["display_url"]
    details["image_width"] = res["data"]["width"]
    details["image_height"] = res["data"]["height"]
    details["image_delete"] = res["data"]["delete_url"]
    product = Product(**details)
    session.add(product)
    session.commit()
    markup = InlineKeyboardMarkup()
    categories = session.query(Category).all()
    markup.add(*[InlineKeyboardButton(i.name,
               callback_data=f"admin_nprod_cat:{product.id}:{i.id}") for i in categories])
    bot.send_message(
        message.chat.id, "Select the category to add the product", reply_markup=markup)


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
            bot.send_message(
                message.chat.id, "Only numbers allowed. Try again")
            bot.register_next_step_handler(message, edit_product, pty, pid)
            return
    elif pty == "discount":
        try:
            product.discount = float(message.text)
        except ValueError:
            bot.send_message(
                message.chat.id, "Only numbers allowed. Try again")
            bot.register_next_step_handler(message, edit_product, pty, pid)
            return
    session.commit()
    if product.discount != 0 and product.discount:
        price_text = f"<s>${product.price}</s> ${product.price-(product.discount*product.price/100)} (-{product.discount}%)"
    else:
        price_text = f"{product.price} (No discount)"
    bot.send_message(message.chat.id, "Product updated !!!")
    bot.send_message(
        message.chat.id, f"Edit Product\nName: {product.name}\nPrice: {price_text}\nDescription: {product.description}", reply_markup=Admin.edit_product(pid))


def edit_image(message, prod_id):
    if is_cancel(message):
        return
    if not message.document:
        bot.send_message(message.chat.id, "Please send the image as a file")
        bot.register_next_step_handler(message, edit_image, prod_id)
        return
    p = session.query(Product).get(prod_id)
    res = ImgBB.upload_file(bot.get_file_url(message.document.file_id))
    if p.image_delete:
        ImgBB.delete_file(p.image_delete)
    p.image = res["data"]["display_url"]
    p.image_width = res["data"]["width"]
    p.image_height = res["data"]["height"]
    p.image_delete = res["data"]["delete_url"]
    session.commit()
    bot.send_message(message.chat.id, p.name+" Image has been replaced!",
                     reply_markup=InlineKeyboardMarkup().add(Admin.back))


def is_cancel(message):
    if message.text in ["/start", "/admin"]:
        bot.clear_step_handler(message)
        bot.send_message(message.chat.id, "Operation cancelled")
        globals()[message.text[1:]](message)
        return True
    return False


def send_invoice(message: Message, product: Product, cat):
    shipping_cost = 6.5 if product.price < 49.99 else 0
    shipping = LabeledPrice("Shipping", int(shipping_cost*100))
    prices = [LabeledPrice(product.name, int(product.price*100))]
    if product.discount != 0 and product.discount:
        prices.append(LabeledPrice("Discount", int(-1*product.discount*product.price)))
    prices.append(shipping)
    bot.send_invoice(
        message.chat.id, product.name, product.description,
        product.name, stripe_token, "eur", prices, photo_url=product.image, photo_width=product.image_width, photo_height=product.image_height, need_email=True, need_shipping_address=True, send_email_to_provider=True, reply_markup=productkb(product.id, cat))


def get_user(user_id):
    user = session.query(Cart).get(user_id)
    if not user:
        user = Cart(id=user_id)
        session.add(user)
        session.commit()
    return user


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message="Something went wrong with the payment. Please Try again.")


@bot.message_handler(content_types=['successful_payment'])
def got_payment(message: Message):
    email = message.successful_payment.order_info.email
    shipping_address = message.successful_payment.order_info.shipping_address
    shipping_text = f"Country code: {shipping_address.country_code}\n"\
        f"State: {shipping_address.state}\n"\
        f"City: {shipping_address.city}\n"\
        f"street line1: {shipping_address.street_line1}\n"\
        f"street line2: {shipping_address.street_line2}\n"\
        f"Post code: {shipping_address.post_code}"
    order = Order(username=message.chat.username,
                  userid=message.chat.id, shipping_address=shipping_text)
    session.add(order)
    if message.successful_payment.invoice_payload == "cart":
        products = get_user(message.chat.id).products
        text = "\n"
        for i in products:
            prod = session.query(Product).get(i.product_id)
            session.add(Orderproduct(name=prod.name, order=order.id))
            text += f"<b>{prod.name}</b> - €{prod.price}\n"
            session.delete(i)
    else:
        text = message.successful_payment.invoice_payload
        session.add(Orderproduct(name=text, order=order.id))
    session.commit()
    bot.send_message(
        message.chat.id, f'Your purchase of {text} was successful✅.\nYour package will be shipped shortly')
    for admin in owners:
        bot.send_message(
            admin, f"Just got a new order from @{message.chat.username} ({email}) for {text}\n\n<b>Shipping Address</b>\n"+shipping_text)


bot.enable_save_next_step_handlers(120)
print("Started")
bot.infinity_polling()
