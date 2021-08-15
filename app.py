from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_cors import CORS

import random
import string

app = Flask(__name__)
app.config[ "SQLALCHEMY_DATABASE_URI"] = "postgresql://utskvbidctbsrq:f590bf9df07389224eba2d12e89d7464e6c595eecc2482c4821132d39d3b40ec@ec2-34-204-128-77.compute-1.amazonaws.com:5432/dae2joimg0snjm"

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

CORS(app)


shelves_table = db.Table('shelves_table',
    db.Column('shelf_id', db.Integer, db.ForeignKey('shelf.id')),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'))
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    token = db.Column(db.String, unique=True)
    shelves = db.relationship("Shelf", backref="user", cascade='all, delete, delete-orphan')
    series = db.relationship("Series", backref="user", cascade='all, delete, delete-orphan')
    books = db.relationship("Book", backref="user", cascade='all, delete, delete-orphan')

    def __init__(self, username, password, token):
        self.username = username
        self.password = password
        self.token = token

class Shelf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    books = db.relationship("Book", secondary="shelves_table")

    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id

class Series(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    books = db.relationship("Book", backref="series")

    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    author = db.Column(db.String, nullable=False)
    published_year = db.Column(db.String)
    number_of_pages = db.Column(db.Integer)
    thumbnail_url = db.Column(db.String)
    read = db.Column(db.Boolean)
    rating = db.Column(db.Integer)
    notes = db.Column(db.String)
    owned = db.Column(db.Boolean)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __init__(self, title, author, published_year, number_of_pages, thumbnail_url, read, rating, notes, owned, series_id, user_id):
        self.title = title
        self.author = author
        self.published_year = published_year
        self.number_of_pages = number_of_pages
        self.thumbnail_url = thumbnail_url
        self.read = read
        self.rating = rating
        self.notes = notes
        self.owned = owned
        self.series_id = series_id
        self.user_id = user_id


class BookSchema(ma.Schema):
    class Meta:
        fields = ("id", "title", "author", "published_year", "number_of_pages", "thumbnail_url", "read", "rating", "notes", "owned", "series_id")

book_schema = BookSchema()
multiple_book_schema = BookSchema(many=True)

class SeriesSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "user_id", "books")
    books = ma.Nested(multiple_book_schema)

series_schema = SeriesSchema()
multiple_series_schema = SeriesSchema(many=True)

class ShelfSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "user_id", "books")
    books = ma.Nested(multiple_book_schema)

shelf_schema = ShelfSchema()
multiple_shelf_schema = ShelfSchema(many=True)

class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "username", "password", "token", "shelves", "series", "books")
    shelves = ma.Nested(multiple_shelf_schema)
    series = ma.Nested(multiple_series_schema)
    books = ma.Nested(multiple_book_schema)

user_schema = UserSchema()
multiple_user_schema = UserSchema(many=True)


def generate_token():
    token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
    while db.session.query(User).filter(User.token == token).first() != None:
        token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
    return token


@app.route("/user/add", methods=["POST"])
def add_user():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    username = post_data.get("username")
    password = post_data.get("password")

    encrypted_password = bcrypt.generate_password_hash(password).decode("utf-8")
    token = generate_token()

    new_record = User(username, encrypted_password, token)
    db.session.add(new_record)
    db.session.commit()

    new_shelf = Shelf("All Books", new_record.id)
    db.session.add(new_shelf) 
    db.session.commit()

    return jsonify(user_schema.dump(new_record))

@app.route("/user/get", methods=["GET"])
def get_all_users():
    all_users = db.session.query(User).all()
    return jsonify(multiple_user_schema.dump(all_users))

@app.route("/user/get/<token>", methods=["GET"])
def get_user_by_id(token):
    user = db.session.query(User).filter(User.token == token).first()

    new_token = generate_token()
    user.token = new_token
    db.session.commit()

    return jsonify(user_schema.dump(user))

@app.route("/user/login", methods=["POST"])
def login():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    username = post_data.get("username")
    password = post_data.get("password")

    user = db.session.query(User).filter(User.username == username).first()
    if user is None:
        return jsonify("Invalid Credentials")

    if bcrypt.check_password_hash(user.password, password) == False:
        return jsonify("Invalid Credentials")

    token = generate_token()
    user.token = token
    db.session.commit()

    return jsonify(user_schema.dump(user))

@app.route("/user/logout/<token>", methods=["DELETE"])
def logout(token):
    user = db.session.query(User).filter(User.token == token).first()
    user.token = None
    db.session.commit()
    return jsonify("Logged Out")


@app.route("/shelf/add", methods=["POST"])
def add_shelf():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    name = post_data.get("name")
    user_id = post_data.get("user_id")

    new_record = Shelf(name, user_id)
    db.session.add(new_record)
    db.session.commit()

    return jsonify(shelf_schema.dump(new_record))

@app.route("/shelf/get", methods=["GET"])
def get_all_shelves():
    all_shelves = db.session.query(Shelf).all()
    return jsonify(multiple_shelf_schema.dump(all_shelves))


@app.route("/series/add", methods=["POST"])
def add_series():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    name = post_data.get("name")
    user_id = post_data.get("user_id")

    new_record = Series(name, user_id)
    db.session.add(new_record)
    db.session.commit()

    return jsonify(series_schema.dump(new_record))

@app.route("/series/get", methods=["GET"])
def get_all_series():
    all_series = db.session.query(Series).all()
    return jsonify(multiple_series_schema.dump(all_series))


@app.route("/book/add", methods=["POST"])
def add_book():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    title = post_data.get("title")
    author = post_data.get("author")
    published_year = post_data.get("published_year")
    number_of_pages = post_data.get("number_of_pages")
    thumbnail_url = post_data.get("thumbnail_url")
    read = post_data.get("read")
    rating = post_data.get("rating")
    notes = post_data.get("notes")
    owned = post_data.get("owned")
    series_id = post_data.get("series_id")
    shelves_ids = post_data.get("shelves_ids")
    user_id = post_data.get("user_id")

    new_record = Book(title, author, published_year, number_of_pages, thumbnail_url, read, rating, notes, owned, series_id, user_id)
    db.session.add(new_record)
    db.session.commit()

    for shelf_id in shelves_ids:
        shelf = db.session.query(Shelf).filter(Shelf.id == shelf_id).first()
        shelf.books.append(new_record)
        db.session.commit()

    return jsonify(book_schema.dump(new_record))

@app.route("/book/get", methods=["GET"])
def get_all_books():
    all_books = db.session.query(Book).all()
    return jsonify(multiple_book_schema.dump(all_books))


if __name__ == "__main__":
    app.run(debug=True)