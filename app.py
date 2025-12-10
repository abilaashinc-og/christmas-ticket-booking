from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "change_this_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.String(50))
    location = db.Column(db.String(100))
    requires_adult = db.Column(db.Boolean, default=True)
    max_tickets_per_booking = db.Column(db.Integer, default=8)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    num_adults = db.Column(db.Integer, default=1)
    num_children = db.Column(db.Integer, default=0)
    seat_type = db.Column(db.String(50))
    adult_photo_filename = db.Column(db.String(200))

    user = db.relationship("User", backref="bookings")
    event = db.relationship("Event", backref="bookings")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Admin access required")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    events = Event.query.all()
    return render_template("index.html", events=events)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        user = User(name=name, email=email, password_hash=hashed, role="user")
        db.session.add(user)
        db.session.commit()
        flash("Registration successful, please log in")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully")
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password")

    return render_template("login.html")


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password")
            return redirect(url_for("admin_login"))

        if user.role != "admin":
            flash("This account is not authorised as admin")
            return redirect(url_for("admin_login"))

        login_user(user)
        flash("Admin login successful")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin_register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if password != confirm:
            flash("Passwords do not match")
            return redirect(url_for("admin_register"))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered")
            return redirect(url_for("admin_register"))

        hashed = generate_password_hash(password)
        admin = User(
            name=name,
            email=email,
            password_hash=hashed,
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()

        flash("Admin account created successfully. Please log in.")
        return redirect(url_for("admin_login"))

    return render_template("admin_register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out")
    return redirect(url_for("index"))


@app.route("/book/<int:event_id>", methods=["GET", "POST"])
@login_required
def book_event(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == "POST":
        num_adults = int(request.form.get("num_adults", 0))
        num_children = int(request.form.get("num_children", 0))
        seat_type = request.form.get("seat_type")
        total_tickets = num_adults + num_children

        if event.requires_adult and num_adults < 1:
            flash("At least one adult is required for this event")
            return redirect(url_for("book_event", event_id=event.id))

        if total_tickets > event.max_tickets_per_booking:
            flash(f"Maximum {event.max_tickets_per_booking} tickets allowed in one booking")
            return redirect(url_for("book_event", event_id=event.id))

        adult_photo = request.files.get("adult_photo")
        filename = None
        if adult_photo and adult_photo.filename:
            filename = secure_filename(adult_photo.filename)
            adult_photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        booking = Booking(
            user_id=current_user.id,
            event_id=event.id,
            num_adults=num_adults,
            num_children=num_children,
            seat_type=seat_type,
            adult_photo_filename=filename,
        )
        db.session.add(booking)
        db.session.commit()
        flash("Booking successful")
        return redirect(url_for("index"))

    return render_template("book_event.html", event=event)


@app.route("/my_bookings")
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template("my_bookings.html", bookings=bookings)


@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template("admin_bookings.html", bookings=bookings)


@app.route("/admin")
@admin_required
def admin_dashboard():
    users = User.query.all()
    return render_template("admin_dashboard.html", users=users)


@app.route("/admin/user/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        user.name = request.form.get("name")
        user.email = request.form.get("email")
        user.role = request.form.get("role")
        db.session.commit()
        flash("User updated")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_edit_user.html", user=user)


@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/create_admin", methods=["GET", "POST"])
@admin_required
def create_admin():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email is already registered")
            return redirect(url_for("create_admin"))

        hashed = generate_password_hash(password)
        new_admin = User(
            name=name,
            email=email,
            password_hash=hashed,
            role="admin",
        )
        db.session.add(new_admin)
        db.session.commit()
        flash("New admin account created successfully")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_admin.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if Event.query.count() == 0:
            circus = Event(
                name="Christmas Circus",
                description="A festive circus show with acrobats, clowns, and live music.",
                date="24 December 2025, 18:00",
                location="Main Big Top Arena",
                requires_adult=True,
                max_tickets_per_booking=8,
            )

            train = Event(
                name="Santa Steam Train",
                description="Ride the historic steam train with Santa and his elves.",
                date="25 December 2025, 14:00",
                location="Park Railway Station",
                requires_adult=True,
                max_tickets_per_booking=8,
            )

            water_show = Event(
                name="Winter Water Show",
                description="Illuminated fountains, music, and light projections over the lake.",
                date="26 December 2025, 19:30",
                location="Park Lakeside Stage",
                requires_adult=False,
                max_tickets_per_booking=10,
            )

            db.session.add_all([circus, train, water_show])
            db.session.commit()
            print("Seeded 3 sample events into the database.")

        admin_user = User.query.filter_by(email="as5752j@gre.ac.uk").first()
        if admin_user and admin_user.role != "admin":
            admin_user.role = "admin"
            db.session.commit()
            print("Promoted as5752j@gre.ac.uk to admin.")

    app.run(host="0.0.0.0", port=5000, debug=True)
