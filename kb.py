from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from models import session, Product, Category

kb = ReplyKeyboardMarkup()
products = KeyboardButton("Prodotti")
shipping = KeyboardButton("Spedizione")
about_us = KeyboardButton("Chi siamo")
contact = KeyboardButton("Contatti")
terms = KeyboardButton("Termini e Condizioni")
faq = KeyboardButton("FAQ")
kb.add(products, shipping)
kb.add(about_us, contact, terms, faq)

class Customer:
    @staticmethod
    def get_categories():
        categorykb = InlineKeyboardMarkup(row_width=2)
        categories = session.query(Category).all()
        for cat in categories:
            btn = InlineKeyboardButton(cat.name, callback_data=f"cp{cat.id}:{cat.products[0].id}")
            categorykb.add(btn)
        return categorykb


class Admin:
    keyboard = InlineKeyboardMarkup()
    add_product = InlineKeyboardButton("Add Product", callback_data="admin_newproduct")
    products = InlineKeyboardButton("Products", callback_data="admin_products")
    keyboard.add(add_product)
    keyboard.add(products)
    keyboard.add(InlineKeyboardButton("Create category", callback_data="admin_create_cat"))

    @staticmethod
    def get_products():
        kb = InlineKeyboardMarkup()
        for prod in session.query(Product).all():
            product = InlineKeyboardButton(prod.name, callback_data=f"admin_p{prod.id}")
            kb.add(product)
        return kb
    
    @staticmethod
    def edit_product(product_id):
        kb = InlineKeyboardMarkup()
        edit_name = InlineKeyboardButton("Edit Name", callback_data=f"admin_en_{product_id}")
        edit_price = InlineKeyboardButton("Edit Price", callback_data=f"admin_ep_{product_id}")
        edit_desc = InlineKeyboardButton("Edit Description", callback_data=f"admin_ed{product_id}")
        back = InlineKeyboardButton("Back", callback_data=f"admin_prod_back")
        kb.add(edit_name, edit_price, edit_desc)
        kb.add(back)
        return kb
    