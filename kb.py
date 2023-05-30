from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from models import session, Product, Category
from copy import deepcopy

kb = ReplyKeyboardMarkup()
products = KeyboardButton("Prodotti")
shipping = KeyboardButton("Spedizione")
cart = KeyboardButton("Carrello")
about_us = KeyboardButton("Chi siamo")
contact = KeyboardButton("Contatti")
terms = KeyboardButton("Termini e Condizioni")
faq = KeyboardButton("FAQ")
kb.add(products, cart, shipping)
kb.add(about_us, contact, terms, faq)

class Customer:
    @staticmethod
    def get_categories():
        categorykb = InlineKeyboardMarkup(row_width=2)
        categories = session.query(Category).all()
        for cat in categories:
            if len(cat.products) > 0:
                btn = InlineKeyboardButton(cat.name, callback_data=f"cp{cat.id}:{cat.products[0].id}")
                categorykb.add(btn)
        return categorykb


class Admin:
    back = InlineKeyboardButton("Indietro", callback_data=f"admin_prod_back")
    pending_order_back = InlineKeyboardButton("Indietro", callback_data=f"admin_pending_orders")
    shipping_order_back = InlineKeyboardButton("Indietro", callback_data=f"admin_shipped_orders")
    cat_back = InlineKeyboardButton("Indietro", callback_data=f"admin_categories")
    home = InlineKeyboardButton("Indietro", callback_data=f"admin_home")
    keyboard = InlineKeyboardMarkup()
    add_product = InlineKeyboardButton("Aggiungi prodotto", callback_data="admin_newproduct")
    products = InlineKeyboardButton("Visualizza i prodotti", callback_data="admin_products")
    categories = InlineKeyboardButton("Visualizza le categorie", callback_data="admin_categories")
    keyboard.add(add_product, InlineKeyboardButton("Creare una categoria", callback_data="admin_create_cat"))
    keyboard.add(products, categories)
    keyboard.add(InlineKeyboardButton("Gestire gli ordini", callback_data="admin_view_orders"), InlineKeyboardButton("Manage Coupons", callback_data="admin_manage_coupon"),
                 InlineKeyboardButton("Modifica del testo", callback_data="admin_edit_text"))

    def get_keyboard(active):
        kb = deepcopy(Admin.keyboard)
        return kb.add(InlineKeyboardButton("Il bot è inattivo 🤖" if not active else "Il bot è attivo ✅", callback_data="admin_toggle_active"))

    view_orders_kb = InlineKeyboardMarkup()
    view_orders_kb.add(InlineKeyboardButton("⌛In attesa", callback_data="admin_pending_orders"), InlineKeyboardButton("🚚 Spedito", callback_data="admin_shipped_orders"))
    view_orders_kb.add(home)

    edit_text_kb = InlineKeyboardMarkup()
    edit_text_kb.add(InlineKeyboardButton("Spedizione", callback_data="admin_text_shipping"), InlineKeyboardButton("Circa", callback_data="admin_text_about")
                     ,InlineKeyboardButton("Contatto", callback_data="admin_text_contact"), InlineKeyboardButton("Termini", callback_data="admin_text_terms")
                     ,InlineKeyboardButton("FAQ", callback_data="admin_text_faq"))

    @staticmethod
    def get_products():
        kb = InlineKeyboardMarkup()
        kb.add(*[InlineKeyboardButton(prod.name, callback_data=f"admin_p{prod.id}") for prod in session.query(Product).all()[::-1]])
        kb.add(Admin.home)
        return kb
    
    @staticmethod
    def edit_product(product_id):
        kb = InlineKeyboardMarkup(row_width=2)
        edit_name = InlineKeyboardButton("Modifica Nome", callback_data=f"admin_en_{product_id}")
        edit_price = InlineKeyboardButton("Modifica Prezzo", callback_data=f"admin_ep_{product_id}")
        edit_desc = InlineKeyboardButton("Modifica Descrizione", callback_data=f"admin_ed_{product_id}")
        edit_image = InlineKeyboardButton("Replace Immagine", callback_data=f"admin_ei_{product_id}")
        edit_category = InlineKeyboardButton("Modifica le categorie", callback_data=f"admin_ec_{product_id}")
        edit_discount = InlineKeyboardButton("Modifica Sconto", callback_data=f"admin_ediscount_{product_id}")
        delete = InlineKeyboardButton("❌ Cancellare", callback_data=f"admin_del_prod:{product_id}")
        kb.add(edit_name, edit_price, edit_desc, edit_category, edit_image, edit_discount)
        kb.add(delete, Admin.back)
        return kb
    
    def edit_category(cat_id):
        kb = InlineKeyboardMarkup(row_width=2)
        edit_name = InlineKeyboardButton("Modifica Nome", callback_data=f"admin_chancatname:{cat_id}")
        # delete = InlineKeyboardButton("❌ DELETE", callback_data=f"admin_catdel:{cat_id}")
        kb.add(edit_name)
        # kb.add(delete)
        kb.add(Admin.cat_back)
        return kb
    
    @staticmethod
    def get_categories():
        categorykb = InlineKeyboardMarkup()
        categories = session.query(Category).all()
        for cat in categories:
            btn = InlineKeyboardButton(cat.name, callback_data=f"admin_editcat:{cat.id}")
            categorykb.add(btn)
        categorykb.add(Admin.home)
        return categorykb

    @staticmethod
    def edit_product_category(product_id):
        kb = InlineKeyboardMarkup(row_width=2)
        categories = session.query(Category).all()
        kb.add(*[InlineKeyboardButton(i.name, callback_data=f"admin_chan_cat:{product_id}:{i.id}") for i in categories])
        kb.add(Admin.back)
        return kb
    