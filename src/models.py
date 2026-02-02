from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    Float,
    ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# =========================
# ACTOR
# =========================
class Actor(Base):
    __tablename__ = "actor"

    actor_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    films = relationship(
        "Film",
        secondary="film_actor",
        back_populates="actors"
    )

    def __repr__(self):
        return f"<Actor(id={self.actor_id}, name={self.first_name} {self.last_name})>"


# =========================
# CATEGORY
# =========================
class Category(Base):
    __tablename__ = "category"

    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    films = relationship(
        "Film",
        secondary="film_category",
        back_populates="categories"
    )

    def __repr__(self):
        return f"<Category(id={self.category_id}, name={self.name})>"


# =========================
# FILM
# =========================
class Film(Base):
    __tablename__ = "film"

    film_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    release_year = Column(Integer)
    rental_rate = Column(Float)
    length = Column(Integer)
    rating = Column(String)

    inventories = relationship(
        "Inventory",
        back_populates="film"
    )

    actors = relationship(
        "Actor",
        secondary="film_actor",
        back_populates="films"
    )

    categories = relationship(
        "Category",
        secondary="film_category",
        back_populates="films"
    )

    def __repr__(self):
        return f"<Film(id={self.film_id}, title={self.title})>"


# =========================
# FILM_ACTOR (tabla puente)
# =========================
class FilmActor(Base):
    __tablename__ = "film_actor"

    actor_id = Column(Integer, ForeignKey("actor.actor_id"), primary_key=True)
    film_id = Column(Integer, ForeignKey("film.film_id"), primary_key=True)


# =========================
# FILM_CATEGORY (tabla puente)
# =========================
class FilmCategory(Base):
    __tablename__ = "film_category"

    film_id = Column(Integer, ForeignKey("film.film_id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("category.category_id"), primary_key=True)


# =========================
# INVENTORY
# =========================
class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True, index=True)
    film_id = Column(Integer, ForeignKey("film.film_id"), nullable=False)
    store_id = Column(Integer, nullable=False)

    film = relationship("Film", back_populates="inventories")

    rentals = relationship(
        "Rental",
        back_populates="inventory"
    )


# =========================
# CUSTOMER
# =========================
class Customer(Base):
    __tablename__ = "customer"

    customer_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String)
    active = Column(Boolean, default=True)

    rentals = relationship("Rental", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")


# =========================
# RENTAL
# =========================
class Rental(Base):
    __tablename__ = "rental"

    rental_id = Column(Integer, primary_key=True, index=True)
    rental_date = Column(Date, nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventory.inventory_id"))
    customer_id = Column(Integer, ForeignKey("customer.customer_id"))
    return_date = Column(Date)

    inventory = relationship("Inventory", back_populates="rentals")
    customer = relationship("Customer", back_populates="rentals")
    payment = relationship("Payment", back_populates="rental", uselist=False)


# =========================
# PAYMENT
# =========================
class Payment(Base):
    __tablename__ = "payment"

    payment_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer.customer_id"))
    rental_id = Column(Integer, ForeignKey("rental.rental_id"))
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, nullable=False)

    customer = relationship("Customer", back_populates="payments")
    rental = relationship("Rental", back_populates="payment")
