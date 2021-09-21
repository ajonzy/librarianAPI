from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

import random
import string

app = Flask(__name__)
app.config[ "SQLALCHEMY_DATABASE_URI"] = "postgresql://utskvbidctbsrq:f590bf9df07389224eba2d12e89d7464e6c595eecc2482c4821132d39d3b40ec@ec2-34-204-128-77.compute-1.amazonaws.com:5432/dae2joimg0snjm"
app.wsgi_app = ProxyFix(app.wsgi_app)

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
    last_used_ip = db.Column(db.String)
    shelves_display = db.Column(db.String, nullable=False)
    shelves = db.relationship("Shelf", backref="user", cascade='all, delete, delete-orphan')
    series = db.relationship("Series", backref="user", cascade='all, delete, delete-orphan')
    books = db.relationship("Book", backref="user", cascade='all, delete, delete-orphan')

    def __init__(self, username, password, token, last_used_ip):
        self.username = username
        self.password = password
        self.token = token
        self.last_used_ip = last_used_ip
        self.shelves_display = "most-books"

class Shelf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    position = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    books = db.relationship("Book", secondary="shelves_table")

    def __init__(self, name, position, user_id):
        self.name = name
        self.position = position
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
    author = db.Column(db.String)
    published_year = db.Column(db.String)
    number_of_pages = db.Column(db.Integer)
    thumbnail_url = db.Column(db.String)
    read = db.Column(db.Boolean)
    rating = db.Column(db.Integer)
    notes = db.Column(db.String)
    owned = db.Column(db.Boolean, nullable=False)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"))
    series_position = db.Column(db.Integer)
    series_data = db.relationship("Series", lazy="subquery", overlaps="books,series")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    shelves = db.relationship("Shelf", secondary="shelves_table", lazy="subquery", overlaps="books")

    def __init__(self, title, author, published_year, number_of_pages, thumbnail_url, read, rating, notes, owned, series_id, series_position, user_id):
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
        self.series_position = series_position
        self.user_id = user_id


class SeriesShallowSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "user_id")

series_shallow_schema = SeriesShallowSchema()
multiple_series_shallow_schema = SeriesShallowSchema(many=True)

class ShelfShallowSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "position", "user_id")

shelf_shallow_schema = ShelfShallowSchema()
multiple_shelf_shallow_schema = ShelfShallowSchema(many=True)

class BookSchema(ma.Schema):
    class Meta:
        fields = ("id", "title", "author", "published_year", "number_of_pages", "thumbnail_url", "read", "rating", "notes", "owned", "series_position", "series_number", "series_id", "series_data", "shelves", "user_id")
    series_data = ma.Nested(series_shallow_schema)
    shelves = ma.Nested(multiple_shelf_shallow_schema)

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
        fields = ("id", "name", "position", "user_id", "books")
    books = ma.Nested(multiple_book_schema)

shelf_schema = ShelfSchema()
multiple_shelf_schema = ShelfSchema(many=True)

# TODO: Remove sensitive data fields
class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "username", "password", "token", "last_used_ip", "shelves_display", "shelves", "series", "books")
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

def generate_return_data(schema):
    if isinstance(schema, dict):
        user = db.session.query(User).filter(User.id == schema.get("user_id")).first()
    elif isinstance(schema, list):
        user = db.session.query(User).filter(User.id == schema[0].get("user_id")).first()
    return {
        "user": user_schema.dump(user),
        "item": schema
    }


@app.route("/user/add", methods=["POST"])
def add_user():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    username = post_data.get("username")
    password = post_data.get("password")

    existing_user_check = db.session.query(User).filter(User.username == username).first()
    if existing_user_check is not None:
        return jsonify("Error: User already exists")

    encrypted_password = bcrypt.generate_password_hash(password).decode("utf-8")
    token = generate_token()
    ip = request.remote_addr

    new_record = User(username, encrypted_password, token, ip)
    db.session.add(new_record)
    db.session.commit()

    new_shelf = Shelf("All Books", 0, new_record.id)
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

    if user is None:
        return jsonify("Invalid Credentials")

    if user.last_used_ip != request.remote_addr:
        user.token = None
        user.last_used_ip = None
        db.session.commit()
        return jsonify("Invalid Credentials")

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
    ip = request.remote_addr
    user.token = token
    user.last_used_ip = ip
    db.session.commit()

    return jsonify(user_schema.dump(user))

@app.route("/user/update/shelves_display/<id>", methods=["PUT"])
def update_user_shelves_display(id):
    user = db.session.query(User).filter(User.id == id).first()

    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    shelves_display = post_data.get("shelves_display")

    user.shelves_display = shelves_display
    db.session.commit()

    return jsonify(user_schema.dump(user))

@app.route("/user/logout/<token>", methods=["DELETE"])
def logout(token):
    user = db.session.query(User).filter(User.token == token).first()
    user.token = None
    user.last_used_ip = None
    db.session.commit()
    return jsonify("Logged Out")


@app.route("/shelf/add", methods=["POST"])
def add_shelf():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    name = post_data.get("name")
    position = post_data.get("position")
    user_id = post_data.get("user_id")

    existing_shelf_check = db.session.query(Shelf).filter(Shelf.name == name).filter(Shelf.user_id == user_id).first()
    if existing_shelf_check is not None:
        return jsonify("Error: Shelf already exists")

    new_record = Shelf(name, position, user_id)
    db.session.add(new_record)
    db.session.commit()

    return_data = generate_return_data(shelf_schema.dump(new_record))
    return jsonify(return_data)

@app.route("/shelf/get", methods=["GET"])
def get_all_shelves():
    all_shelves = db.session.query(Shelf).all()
    return_data = generate_return_data(multiple_shelf_schema.dump(all_shelves))
    return jsonify(return_data)

@app.route("/shelf/update/<id>", methods=["PUT"])
def update_shelf(id):
    shelf = db.session.query(Shelf).filter(Shelf.id == id).first()

    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    name = post_data.get("name")
    position = post_data.get("position")

    if shelf.name != name:
        existing_shelf_check = db.session.query(Shelf).filter(Shelf.name == name).filter(Shelf.user_id == shelf.user_id).first()
        if existing_shelf_check is not None:
            return jsonify("Error: Shelf already exists")

    if shelf.position != position and position is not None:
        moved_shelves = db.session.query(Shelf).filter(Shelf.position <= position if shelf.position < position else Shelf.position >= position).filter(Shelf.position > shelf.position if shelf.position < position else Shelf.position < shelf.position).all()
        for moved_shelf in moved_shelves:
            moved_shelf.position = moved_shelf.position - 1 if shelf.position < position else moved_shelf.position + 1
            db.session.commit()

    shelf.name = name
    shelf.position = position
    db.session.commit()

    return_data = generate_return_data(shelf_schema.dump(shelf))
    return jsonify(return_data)

@app.route("/shelf/delete/<id>", methods=["DELETE"])
def delete_shelf(id):
    shelf = db.session.query(Shelf).filter(Shelf.id == id).first()

    moved_shelves = db.session.query(Shelf).filter(Shelf.position > shelf.position).all()
    for moved_shelf in moved_shelves:
        moved_shelf.position -= 1
        db.session.commit()

    db.session.delete(shelf)
    db.session.commit()
    return_data = generate_return_data(shelf_schema.dump(shelf))
    return jsonify(return_data)


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

    return_data = generate_return_data(series_schema.dump(new_record))
    return jsonify(return_data)

@app.route("/series/get", methods=["GET"])
def get_all_series():
    all_series = db.session.query(Series).all()
    return_data = generate_return_data(multiple_series_schema.dump(all_series))
    return jsonify(return_data)

@app.route("/series/update/<id>", methods=["PUT"])
def update_series(id):
    series = db.session.query(Series).filter(Series.id == id).first()

    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    name = post_data.get("name")
    book_positions = post_data.get("book_positions")

    if series.name != name:
        existing_series_check = db.session.query(Series).filter(Series.name == name).filter(Series.user_id == series.user_id).first()
        if existing_series_check is not None:
            return jsonify("Error: Series already exists")

    series.name = name
    db.session.commit()

    for book_position in book_positions:
        book = db.session.query(Book).filter(Book.id == book_position.get("id")).first()
        book.series_position = book_position.get("position")
        db.session.commit()

    return_data = generate_return_data(series_schema.dump(series))
    return jsonify(return_data)

@app.route("/series/delete/<id>", methods=["DELETE"])
def delete_series(id):
    series = db.session.query(Series).filter(Series.id == id).first()
    db.session.delete(series)
    db.session.commit()
    return_data = generate_return_data(series_schema.dump(series))
    return jsonify(return_data)


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
    series_position = post_data.get("series_position")
    shelves_ids = post_data.get("shelves_ids")
    user_id = post_data.get("user_id")

    new_record = Book(title, author, published_year, number_of_pages, thumbnail_url, read, rating, notes, owned, series_id, series_position, user_id)
    db.session.add(new_record)
    db.session.commit()

    for shelf_id in shelves_ids:
        shelf = db.session.query(Shelf).filter(Shelf.id == shelf_id).first()
        shelf.books.append(new_record)
        db.session.commit()

    return_data = generate_return_data(book_schema.dump(new_record))
    return jsonify(return_data)

@app.route("/book/get", methods=["GET"])
def get_all_books():
    all_books = db.session.query(Book).all()
    return_data = generate_return_data(multiple_book_schema.dump(all_books))
    return jsonify(return_data)

@app.route("/book/update/<id>", methods=["PUT"])
def update_book(id):
    book = db.session.query(Book).filter(Book.id == id).first()

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
    series_position = post_data.get("series_position")
    shelves_ids = post_data.get("shelves_ids")

    book.title = title
    book.author = author
    book.published_year = published_year
    book.number_of_pages = number_of_pages
    book.thumbnail_url = thumbnail_url
    book.read = read
    book.rating = rating
    book.notes = notes
    book.series_id = series_id
    book.series_position = series_position
    db.session.commit()

    for nestedShelf in book.shelves:
        shelf = db.session.query(Shelf).filter(Shelf.id == nestedShelf.id).first()
        shelf.books = list(filter(lambda nestedBook: nestedBook.id != book.id, shelf.books))
        db.session.commit()

    for shelf_id in shelves_ids:
        shelf = db.session.query(Shelf).filter(Shelf.id == shelf_id).first()
        shelf.books.append(book)
        db.session.commit()

    return_data = generate_return_data(book_schema.dump(book))
    return jsonify(return_data)

@app.route("/book/delete/<id>", methods=["DELETE"])
def delete_book(id):
    book = db.session.query(Book).filter(Book.id == id).first()
    db.session.delete(book)
    db.session.commit()
    return_data = generate_return_data(book_schema.dump(book))
    return jsonify(return_data)


if __name__ == "__main__":
    app.run(debug=True)