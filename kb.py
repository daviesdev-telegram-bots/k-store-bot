from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from models import session, Product, Category

kb = ReplyKeyboardMarkup()
products = KeyboardButton("Prodotti")
shipping = KeyboardButton("Spedizione")
cart = KeyboardButton("Cart")
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
    back = InlineKeyboardButton("Back", callback_data=f"admin_prod_back")
    cat_back = InlineKeyboardButton("Back", callback_data=f"admin_cat_back")
    home = InlineKeyboardButton("Back", callback_data=f"admin_home")
    keyboard = InlineKeyboardMarkup()
    add_product = InlineKeyboardButton("Add Product", callback_data="admin_newproduct")
    products = InlineKeyboardButton("View Products", callback_data="admin_products")
    categories = InlineKeyboardButton("View Categories", callback_data="admin_categories")
    keyboard.add(add_product)
    keyboard.add(InlineKeyboardButton("Create category", callback_data="admin_create_cat"))
    keyboard.add(products)
    keyboard.add(categories)

    @staticmethod
    def get_products():
        kb = InlineKeyboardMarkup()
        kb.add(*[InlineKeyboardButton(prod.name, callback_data=f"admin_p{prod.id}") for prod in session.query(Product).all()[::-1]])
        kb.add(Admin.home)
        return kb
    
    @staticmethod
    def edit_product(product_id):
        kb = InlineKeyboardMarkup(row_width=2)
        edit_name = InlineKeyboardButton("Edit Name", callback_data=f"admin_en_{product_id}")
        edit_price = InlineKeyboardButton("Edit Price", callback_data=f"admin_ep_{product_id}")
        edit_desc = InlineKeyboardButton("Edit Description", callback_data=f"admin_ed_{product_id}")
        edit_image = InlineKeyboardButton("Replace Image", callback_data=f"admin_ei_{product_id}")
        edit_category = InlineKeyboardButton("Edit Category", callback_data=f"admin_ec_{product_id}")
        delete = InlineKeyboardButton("❌ DELETE", callback_data=f"admin_del:{product_id}")
        kb.add(edit_name, edit_price, edit_desc, edit_category, edit_image)
        kb.add(delete, Admin.back)
        return kb
    
    def edit_category(cat_id):
        kb = InlineKeyboardMarkup(row_width=2)
        edit_name = InlineKeyboardButton("Edit Name", callback_data=f"admin_chancatname:{cat_id}")
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
    