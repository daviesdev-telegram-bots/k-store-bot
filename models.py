from sqlalchemy import Float, create_engine, Column, Text, Integer, ForeignKey, Boolean, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import dotenv, os
dotenv.load_dotenv()

base = declarative_base()

class Product(base):
    __tablename__ = "product"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    description = Column(Text)
    price = Column(Float)
    discount = Column(Float, default=0.0)
    shipping = Column(Text, nullable=True)
    image = Column(Text, nullable=True, default=None)
    image_delete = Column(Text, nullable=True, default=None)
    image_height = Column(Integer, nullable=True, default=None)
    image_width = Column(Integer, nullable=True, default=None)
    category = Column(Integer, ForeignKey('category.id'), nullable=True)

class Category(base):
    __tablename__ = "category"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    products = relationship('Product')

class Cart(base):
    __tablename__ = "cart"
    id = Column(Integer, primary_key=True)
    products = relationship('Cartproduct')

class Cartproduct(base):
    __tablename__ = "cartproduct"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    cart = Column(Integer, ForeignKey('cart.id'), nullable=True)

class Orderproduct(base):
    __tablename__ = "orderproduct"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    order = Column(Integer, ForeignKey('order.id'), nullable=True)

class Order(base):
    __tablename__ = "order"
    id = Column(Integer, primary_key=True)
    userid = Column(Integer)
    username = Column(String(200))
    shipped = Column(Boolean, default=False)
    shipping_address = Column(Text)
    products = relationship("Orderproduct")

class Coupon(base):
    __tablename__ = "coupon"
    id = Column(Integer, primary_key=True)
    code = Column(Text)
    discount = Column(Float)
    is_percent = Column(Boolean)

engine = create_engine(os.getenv("DB_URL"))
connection = engine.connect()
base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()