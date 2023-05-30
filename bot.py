from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, LabeledPrice, Message
from dotenv import load_dotenv
import os
import json
import random
from imgbb import ImgBB
from kb import *
from models import session, Product, Cart, Cartproduct, Order, Orderproduct, Coupon

load_dotenv()

bot_token = os.getenv("bot_token")
stripe_token = os.getenv("stripe_token")
owners = json.loads(os.getenv("owners"))
bot = TeleBot(bot_token, parse_mode="HTML")
active = True

with open("text.json") as f:
    text_data = json.load(f)

def productkb(i, cat):
    category = session.query(Category).get(cat).products
    fproduct, lproduct = category[0], category[-1]
    prod = session.query(Product).get(i)
    index = category.index(prod)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Acquista", pay=True), InlineKeyboardButton(
        "🛒 Aggiungi al carrello", callback_data=f"+cart{i}"))
    if i != fproduct.id:
        prev = InlineKeyboardButton(
            "🔼 Precedente", callback_data=f"cp{cat}:{category[index-1].id}")
        kb.add(prev)
    if i != lproduct.id:
        next_ = InlineKeyboardButton(
            "🔽 Avanti", callback_data=f"cp{cat}:{category[index+1].id}")
        kb.add(next_)
    return kb

def set_active(v):
    global active
    active = v
    return v


@bot.message_handler(["start"])
def start(message):
    if not active:
        bot.send_message(message.chat.id, "Il bot 🤖 non è attivo al momento. Riprova più tardi!")
        return
    bot.send_message(
        message.chat.id, "<b>Ciao benvenuto nel negozio!!!</b>", reply_markup=kb)


@bot.message_handler(["admin"], func=lambda message: message.chat.id in owners)
def admin(message):
    bot.send_message(
        message.chat.id, "<b>Ciao Admin !</b> Cosa vuoi modificare oggi?", reply_markup=Admin.get_keyboard(active))

@bot.message_handler(["carrello"])
def view_cart(message):
    if not active:
        bot.send_message(message.chat.id, "Il bot 🤖 non è attivo al momento. Riprova più tardi!")
        return
    kb = InlineKeyboardMarkup(row_width=2)
    user = session.query(Cart).get(message.chat.id)
    if not user or len(user.products) <= 0:
        bot.send_message(
            message.chat.id, "Il tuo carrello è vuoto!\n\nClicca su /prodotti per navigare")
        return
    for p in user.products:
        prod = session.query(Product).get(p.product_id)
        kb.add(InlineKeyboardButton(prod.name, callback_data=f"{prod.id}"), InlineKeyboardButton(
            "🗑️ Rimuovere", callback_data=f"-cart:{prod.id}"))
    kb.add(InlineKeyboardButton("Cassa", callback_data="checkout"))
    bot.send_message(message.chat.id, "<b>Carrello !</b>", reply_markup=kb)


@bot.message_handler(["prodotti"])
def list_products(message):
    if not active:
        bot.send_message(message.chat.id, "Il bot 🤖 non è attivo al momento. Riprova più tardi!")
        return
    bot.send_message(message.chat.id, "Quale categoria desidera sfogliare?",
                     reply_markup=Customer.get_categories())


@bot.message_handler(func=lambda msg: msg.text != None)
def message_handler(message: Message):
    if not active:
        bot.send_message(message.chat.id, "Il bot 🤖 non è attivo al momento. Riprova più tardi!")
        return
    elif message.text == "Prodotti":
        list_products(message)
    elif message.text == "Carrello":
        view_cart(message)
    elif message.text == "Spedizione":
        bot.send_message(message.chat.id, text_data["shipping"])
    elif message.text == "Chi siamo":
        bot.send_message(message.chat.id, text_data["about"])
    elif message.text == "Contatti":
        bot.send_message(message.chat.id, text_data["contact"])
    elif message.text == "Termini e Condizioni":
        bot.send_message(message.chat.id, text_data["terms"])
    elif message.text == "FAQ":
        bot.send_message(message.chat.id, text_data["faq"])

@bot.callback_query_handler(func=lambda call: call.data != None)
def callback_handler(call: CallbackQuery):
    message = call.message

    if not call.data.startswith("admin_") and not active:
        bot.send_message(message.chat.id, "Il bot 🤖 non è attivo al momento. Riprova più tardi!")
        return

    if call.data.startswith("cp"):
        cat, prod = call.data.strip("cp").split(":")
        product = session.query(Product).filter_by(
            id=int(prod), category=int(cat)).first()
        bot.delete_message(message.chat.id, message.id)
        if not product:
            bot.send_message(message.chat.id, "Il prodotto non è disponibile!☹️")
            return
        send_invoice(message, product, cat)

    elif call.data.startswith("+cart"):
        prod_id = call.data[5:]
        user = get_user(message.chat.id)
        session.add(Cartproduct(product_id=int(prod_id), cart=user.id))
        session.commit()
        bot.answer_callback_query(call.id, f"Aggiunto al carrello✅", True)

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
                "🗑️ Rimuovere", callback_data=f"-cart:{prod.id}"))
        kb.add(InlineKeyboardButton("Cassa", callback_data=f"checkout"))
        bot.edit_message_text(
            f"Totale: €{total}", message.chat.id, message.id, reply_markup=kb)

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
        prices.append(LabeledPrice("Sconto", -int(discount)))
        prices.append(LabeledPrice("Spedizione", int(shipping_cost*100)))
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Pay", pay=True))
        bot.send_invoice(message.chat.id, "Il vostro ordine", ", ".join(text), "cart", stripe_token, "eur", prices,
                         need_email=True, need_shipping_address=True, send_email_to_provider=True, reply_markup=kb)
        bot.send_message(message.chat.id, "Inviare un codice coupon se lo si possiede.\nSe non lo si possiede, proseguire con il checkout con il pulsante qui sopra☝️!")
        bot.register_next_step_handler(message, get_coupon_code, message.id)

    if call.data.startswith("admin_") and message.chat.id in owners:
        data = call.data[6:]
        if data == "toggle_active":
            a = set_active(not active)
            bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup=Admin.get_keyboard(a))

        if data == "newproduct":
            bot.send_message(message.chat.id, "Qual è il nome del prodotto?")
            bot.register_next_step_handler(message, add_product)
        elif data in ["products", "prod_back"]:
            bot.clear_step_handler(message)
            bot.edit_message_text(
                "Seleziona il prodotto", message.chat.id, message.id, reply_markup=Admin.get_products())

        elif data == "edit_text":
            bot.edit_message_text("What text do you want to edit?", message.chat.id, message.id, reply_markup=Admin.edit_text_kb)

        elif data  == "categories":
            bot.clear_step_handler(message)
            bot.edit_message_text("Selezionare una categoria", message.chat.id,
                                  message.id, reply_markup=Admin.get_categories())

        elif data == "home":
            bot.edit_message_text("<b>Ciao Admin !</b> Cosa vuoi modificare oggi?",
                                  message.chat.id, message.id, reply_markup=Admin.get_keyboard(active))

        elif data.startswith("p") and data[1:].isdigit():
            product = session.query(Product).get(int(data[1:]))
            if product.discount != 0 and product.discount:
                price_text = f"<s>${product.price}</s> ${product.price-(product.discount*product.price/100)} (-{product.discount}%)"
            else:
                price_text = f"${product.price} (Nessuno sconto)"
            bot.edit_message_text(f"Modifica prodotto\nNome: {product.name}\nPrezzo: {price_text}\nDescrizione: {product.description}",
                                  message.chat.id, message.id, parse_mode="HTML", reply_markup=Admin.edit_product(data[1:]))

        elif data.startswith("editcat"):
            _, cat_id = data.split(":")
            category = session.query(Category).get(cat_id)
            bot.edit_message_text(f"Nome: {category.name}", message.chat.id,
                                  message.id, reply_markup=Admin.edit_category(cat_id))

        elif data.startswith("e") and data[1] in ["n", "p", "d", "c", "i"]:
            product_id = data[3:]
            if data[1] == "c":
                bot.edit_message_text(f"Selezionare la categoria in cui si vuole trasferire il prodotto",
                                      message.chat.id, message.id, reply_markup=Admin.edit_product_category(product_id))
                return
            elif data[1] == "i":
                bot.edit_message_text(f"Inviare l'immagine che si desidera utilizzare", message.chat.id,
                                      message.id, reply_markup=InlineKeyboardMarkup().add(Admin.back))
                bot.register_next_step_handler(message, edit_image, product_id)
                return
            elif data.split("_")[0] == "ediscount":
                prop = "discount"
                product_id = data.split("_")[-1]
            else:
                prop = data[1]
            n = {"n": "nome", "p": "prezzo", "d": "descrizione", "discount": "sconto (%)"}
            bot.send_message(message.chat.id, f"Inviare il nuovo {n[prop]}.\nUsare /cancel per interrompere il processo")
            bot.register_next_step_handler(message, edit_product, prop, product_id)

        elif data.startswith("create_cat"):
            bot.send_message(
                message.chat.id, "Qual è il nome della categoria?")
            bot.register_next_step_handler(message, new_category)

        elif data.startswith("chancatname"):
            _, cat_id = data.split(":")
            bot.send_message(
                message.chat.id, f"Come si vuole cambiare il nome della categoria?")
            bot.register_next_step_handler(
                message, change_category_name, cat_id)

        elif data.startswith("del_prod"):
            _, prod_id = data.split(":")
            name = session.query(Product).get(int(prod_id)).name
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("✅Sì", callback_data=f"admin_confirm_del:{prod_id}"), InlineKeyboardButton(
                "❌ No", callback_data=f"admin_prod_back"))
            bot.edit_message_text("Sei sicuro di voler CANCELLARE" +
                                  name.upper(), message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("confirm_del"):
            _, prod_id = data.split(":")
            prod = session.query(Product).get(int(prod_id))
            session.delete(prod)
            session.commit()
            kb = InlineKeyboardMarkup().add(Admin.back)
            bot.edit_message_text(
                prod.name+" è stato cancellato", message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("chan_cat"):
            _, prod_id, cat_id = data.split(":")
            product = session.query(Product).get(int(prod_id))
            product.category = cat_id
            session.commit()
            kb = InlineKeyboardMarkup().add(Admin.back)
            bot.edit_message_text(f"{product.name}'s la categoria è stata aggiornata!",
                                  message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("nprod_cat"):
            _, prod_id, cat_id = data.split(":")
            session.query(Product).get(int(prod_id)).category = cat_id
            session.commit()
            bot.send_message(message.chat.id, "Prodotto aggiunto con successo!",
                             reply_markup=InlineKeyboardMarkup().add(Admin.back))

        elif data.startswith("del_coupon"):
            _, c_id = data.split(":")
            c = session.query(Coupon).get(c_id)
            session.delete(c)
            session.commit()
            bot.answer_callback_query(call.id, f"{c.code} cancellato", True)
            kb = InlineKeyboardMarkup()
            coupons = session.query(Coupon).all()
            for coupon in coupons:
                if coupon.is_percent: t = f"{coupon.discount}%"
                else: t = f"${coupon.discount}"
                kb.add(InlineKeyboardButton(f"{coupon.code} (-{t})", callback_data=f"c.id"), InlineKeyboardButton("🗑️ Cancellare", callback_data=f"admin_del_coupon:{coupon.id}"))
            kb.add(InlineKeyboardButton("➕ Nuovo Coupon", callback_data="admin_new_coupon"), Admin.home)
            bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup=kb)

        elif data == "manage_coupon":
            coupons = session.query(Coupon).all()
            kb = InlineKeyboardMarkup()
            for coupon in coupons:
                if coupon.is_percent: t = f"{coupon.discount}%"
                else: t = f"${coupon.discount}"
                kb.add(InlineKeyboardButton(f"{coupon.code} (-{t})", callback_data=f"c.id"), InlineKeyboardButton("🗑️ Cancellare", callback_data=f"admin_del_coupon:{coupon.id}"))
            kb.add(InlineKeyboardButton("➕ Nuovo Coupon", callback_data="admin_new_coupon"), Admin.home)
            bot.edit_message_text("Buoni", message.chat.id, message.id, reply_markup=kb)

        elif data == "new_coupon":
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("Percentuale", callback_data=f"admin_newcoupon_percent"), InlineKeyboardButton("Prezzo", callback_data=f"admin_newcoupon_price"))
            kb.add(InlineKeyboardButton("Indietro", callback_data="admin_manage_coupon"))
            bot.edit_message_text("Che tipo di coupon si vuole creare", message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("newcoupon_"):
            coupon_type = data[10:]
            if coupon_type == "percent":
                text = "Quante % di sconto?"
            elif coupon_type == "price":
                text = "Quanti dollari di sconto?"
            else: return
            bot.send_message(message.chat.id, text+"\nInviare solo numeri (ad es. 20).\nUtilizzare /cancel al processo")
            bot.register_next_step_handler(message, coupon_value, coupon_type)

        elif data == "view_orders":
            bot.edit_message_text(
                "Scegliere", message.chat.id, message.id, reply_markup=Admin.view_orders_kb)

        elif data in ["pending_orders", "shipped_orders"]:
            pending_orders = session.query(Order).filter_by(
                shipped=data != "pending_orders").all()
            kb = InlineKeyboardMarkup()
            kb.add(*[InlineKeyboardButton("@"+order.username,
                   callback_data=f"admin_order_details:{order.id}") for order in pending_orders])
            kb.add(InlineKeyboardButton(
                "Indietro", callback_data="admin_view_orders"))
            bot.edit_message_text("Ecco tutti gli individui con ordini in sospeso",
                                  message.chat.id, message.id, reply_markup=kb)

        elif data.startswith("order_details"):
            _, orderid = data.split(":")
            order_details = session.query(Order).get(orderid)
            products = ""
            for i in order_details.products:
                products += f"<b>{i.name}</b>\n"
            kb = InlineKeyboardMarkup()
            if not order_details.shipped:
                kb.add(InlineKeyboardButton("Contrassegnare come spedito", callback_data="admin_mark_shipped:"+str(orderid)))
            kb.add(Admin.pending_order_back if not order_details.shipped else Admin.shipping_order_back)
            bot.edit_message_text(f"Nome utente: @{bot.get_chat(order_details.userid).username}\nSpedizione: {'Spedito' if order_details.shipped else 'Non spedito'}\n\Prodotti\n{products}\n{order_details.shipping_address}", message.chat.id,
                                  message.id, reply_markup=kb)

        elif data.startswith("mark_shipped"):
            _, orderid = data.split(":")
            order = session.query(Order).get(orderid)
            order.shipped = True
            session.commit()
            bot.edit_message_text("Ordine contrassegnato come spedito ✅", message.chat.id, message.id,
                                  reply_markup=InlineKeyboardMarkup().add(Admin.pending_order_back))
        
        elif data.startswith("text_"):
            field = data[5:]
            bot.send_message(message.chat.id, f"Messaggio attuale\n\n{text_data.get(field)}\n\nInviare il nuovo messaggio che si desidera impostare.\nInviare /cancel per interrompere questo processo")
            bot.register_next_step_handler(message, new_text, field)

def new_text(message, field):
    if is_cancel(message):
        return
    if message.text:
        text_data[field] = message.text
        bot.send_message(message.chat.id, f"{field} il testo è stato aggiornato", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Back", callback_data="admin_edit_text")))
        save_text_data()
        return
    bot.register_next_step_handler(message, field)

def save_text_data():
    global text_data
    with open("text.json", "w") as f:
        json.dump(text_data, f)

def get_coupon_code(message, former_message_id):
    if is_cancel(message):
        return
    if message.text:
        coupon = session.query(Coupon).filter_by(code=message.text.upper()).first()
        if coupon:
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
                total += prod.price
                text.append(f"{prod.name} - €{prod.price}")
            total -= discount/100
            if coupon.is_percent:
                v = -total*coupon.discount
            else:
                v = -coupon.discount*100
            shipping_cost = 6.5 if total < 49.99 else 0
            prices.append(LabeledPrice("Sconto", -int(discount)))
            prices.append(LabeledPrice("Coupon", int(v)))
            prices.append(LabeledPrice("Spedizione", int(shipping_cost*100)))
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("Pay", pay=True))
            bot.send_invoice(message.chat.id, "Il vostro ordine", ", ".join(text), "cart", stripe_token, "eur", prices,
                            need_email=True, need_shipping_address=True, send_email_to_provider=True, reply_markup=kb)
            bot.delete_message(message.chat.id, former_message_id)
        else:
            bot.send_message(message.chat.id, "Codice coupon errato")
        return
    bot.register_next_step_handler(message, get_coupon_code, former_message_id)

def coupon_value(message, coupon_type):
    if is_cancel(message):
        return
    try:
        float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Sono ammessi solo numeri. Riprova")
        bot.register_next_step_handler(message, coupon_value, coupon_type)
        return
    bot.send_message(message.chat.id, "Quale sarà il codice del coupon?\nInviate /random per darne uno a caso")
    bot.register_next_step_handler(message, create_coupon, coupon_type, float(message.text))

def create_coupon(message, coupon_type, coupon_value):
    if is_cancel(message):
        return
    if message.text == "/random":
        code = random_coupon_code()
    else:
        code = message.text
    coupon = Coupon(code=code.upper(), discount=coupon_value, is_percent=coupon_type == "percent")
    session.add(coupon)
    session.commit()
    bot.send_message(message.chat.id, f"Il coupon <b>{code.upper()}</b> è stato creato", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Indietro", callback_data="admin_manage_coupon")))

letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def random_coupon_code():
    return ''.join(random.choice(letters) for x in range(7))

def new_category(message):
    if message.text:
        if is_cancel(message):
            return
        category = Category(name=message.text)
        session.add(category)
        session.commit()
        bot.send_message(message.chat.id, "Categoria creata",
                         reply_markup=InlineKeyboardMarkup().add(Admin.cat_back))
    else:
        bot.send_message(message.chat.id, "Si prega di inviare un messaggio di testo")
        bot.register_next_step_handler(message, new_category)


def change_category_name(message, cat_id):
    if message.text:
        if is_cancel(message):
            return
        category = session.query(Category).get(cat_id)
        category.name = message.text
        session.commit()
        bot.send_message(message.chat.id, "Nome della categoria modificato in" +
                         message.text, reply_markup=InlineKeyboardMarkup().add(Admin.cat_back))
    else:
        bot.send_message(message.chat.id, "Si prega di inviare un messaggio di testo")
        bot.register_next_step_handler(message, change_category_name)


def add_product(message):
    if is_cancel(message):
        return
    bot.send_message(
        message.chat.id, "Qual è il prezzo (in €), ad esempio 100, 200 e.t.c.")
    details = {"name": message.text}
    bot.register_next_step_handler(message, add_price, details)


def add_price(message, details):
    if is_cancel(message):
        return
    try:
        details["price"] = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Sono ammessi solo numeri. Riprova")
        bot.register_next_step_handler(message, add_price, details)
        return
    bot.send_message(message.chat.id, "Qual è la descrizione?")
    bot.register_next_step_handler(message, add_desc, details)


def add_desc(message, details):
    if is_cancel(message):
        return
    details["description"] = message.text
    bot.send_message(message.chat.id, "Inviare l'immagine del prodotto")
    bot.register_next_step_handler(message, add_image, details)


def add_image(message: Message, details):
    if is_cancel(message):
        return
    if not message.document:
        bot.send_message(message.chat.id, "Si prega di inviare l'immagine come file")
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
        message.chat.id, "Selezionare la categoria in cui aggiungere il prodotto", reply_markup=markup)


def edit_product(message, pty, pid):
    if is_cancel(message):
        return
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
                message.chat.id, "Sono ammessi solo numeri. Riprova")
            bot.register_next_step_handler(message, edit_product, pty, pid)
            return
    elif pty == "discount":
        try:
            product.discount = float(message.text)
        except ValueError:
            bot.send_message(
                message.chat.id, "Sono ammessi solo numeri. Riprova")
            bot.register_next_step_handler(message, edit_product, pty, pid)
            return
    session.commit()
    if product.discount != 0 and product.discount:
        price_text = f"<s>${product.price}</s> ${product.price-(product.discount*product.price/100)} (-{product.discount}%)"
    else:
        price_text = f"{product.price} (Nessuno sconto)"
    bot.send_message(message.chat.id, "Prodotto aggiornato !!!")
    bot.send_message(
        message.chat.id, f"Modifica del prodotto\nNome: {product.name}\nPrezzo: {price_text}\nDescrizione: {product.description}", reply_markup=Admin.edit_product(pid))


def edit_image(message, prod_id):
    if is_cancel(message):
        return
    if not message.document:
        bot.send_message(message.chat.id, "Si prega di inviare l'immagine come file")
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
    bot.send_message(message.chat.id, p.name+" L'immagine è stata sostituita!",
                     reply_markup=InlineKeyboardMarkup().add(Admin.back))


def is_cancel(message):
    if message.text in ["/start", "/admin", "/cancel"]:
        bot.clear_step_handler(message)
        bot.send_message(message.chat.id, "Operazione annullata")
        if message.text != "/cancel":
            globals()[message.text[1:]](message)
        return True
    return False


def send_invoice(message: Message, product: Product, cat):
    shipping_cost = 6.5 if product.price < 49.99 else 0
    shipping = LabeledPrice("Spedizione", int(shipping_cost*100))
    prices = [LabeledPrice(product.name, int(product.price*100))]
    if product.discount != 0 and product.discount:
        prices.append(LabeledPrice("Sconto", int(-1*product.discount*product.price)))
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
                                  error_message="Qualcosa è andato storto con il pagamento. Si prega di riprovare.")


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
        message.chat.id, f'Il tuo acquisto di {text} è andato a buon fine✅.\nIl tuo pacco sarà spedito a breve')
    for admin in owners:
        bot.send_message(
            admin, f"Ho appena ricevuto un nuovo ordine da @{message.chat.username} ({email}) for {text}\n\n<b>Spedizione Indirizzo</b>\n"+shipping_text)

print("Started")
bot.infinity_polling()
