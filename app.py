from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_cors import CORS

app = Flask(__name__)
app.config[ "SQLALCHEMY_DATABASE_URI"] = "postgresql://utskvbidctbsrq:f590bf9df07389224eba2d12e89d7464e6c595eecc2482c4821132d39d3b40ec@ec2-34-204-128-77.compute-1.amazonaws.com:5432/dae2joimg0snjm"

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

CORS(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = password

class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "username")

user_schema = UserSchema()
multiple_user_schema = UserSchema(many=True)


@app.route("/user/add", methods=["POST"])
def add_user():
    if request.content_type != "application/json":
        return jsonify("Error: Data must be sent as JSON")

    post_data = request.get_json()
    username = post_data.get("username")
    password = post_data.get("password")

    encrypted_password = bcrypt.generate_password_hash(password)

    new_record = User(username, encrypted_password)
    db.session.add(new_record)
    db.session.commit()

    return jsonify(user_schema.dump(new_record))

@app.route("/user/get", methods=["GET"])
def get_all_users():
    all_users = db.session.query(User).all()
    return jsonify(multiple_user_schema.dump(all_users))

@app.route("/user/get/id/<id>", methods=["GET"])
def get_user_by_id(id):
    user = db.session.query(User).filter(User.id == id).first()
    return jsonify(user_schema.dump(user))

@app.route("user/get/username/<username>", methods=["GET"])
def get_user_by_username(username):
    user = db.session.query(User).filter(User.username == username).first()
    return jsonify(user_schema.dump(user))


if __name__ == "__main__":
    app.run(debug=True)