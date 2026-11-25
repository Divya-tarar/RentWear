from functools import wraps
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import Error, IntegrityError

from database.db_connection import get_db_connection
from database.mongo_connection import log_activity
import os
from dotenv import load_dotenv

load_dotenv()


# ==========================================================
# 1. FLASK CONFIGURATION
# ==========================================================

app = Flask(__name__,
            static_folder="public/static",
            static_url_path="/static",)
app.secret_key = os.getenv("SECRET_KEY", "rentwear-development-key-change-before-deployment")


# ==========================================================
# 2. COMMON HELPERS AND ACCESS CONTROL
# ==========================================================

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return "Access denied! Admins only.", 403
        return func(*args, **kwargs)
    return wrapper


def close_db(cursor=None, connection=None):
    try:
        if cursor is not None:
            cursor.close()
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def get_connection_or_error():
    connection = get_db_connection()
    if connection is None:
        return None, None, ("Database connection failed. Check your database settings.", 500)
    return connection, connection.cursor(dictionary=True), None


# ==========================================================
# 3. CUSTOMER-FACING PAGES
# ==========================================================

@app.route("/")
def home():
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("""
            SELECT * FROM products
            WHERE availability_status = 'available'
            ORDER BY created_at DESC
        """)
        products = cursor.fetchall()
        return render_template("index.html", products=products)
    except Error as error:
        app.logger.exception("Home page database error: %s", error)
        return "Unable to load the homepage.", 500
    finally:
        close_db(cursor, connection)


@app.route("/products")
def products_page():
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response

    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()

    try:
        query = """
            SELECT p.*, c.category_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            WHERE p.availability_status = 'available'
        """
        params = []
        if search:
            query += " AND (p.product_name LIKE %s OR p.description LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        if category_id.isdigit():
            query += " AND p.category_id = %s"
            params.append(int(category_id))
        query += " ORDER BY p.created_at DESC"

        cursor.execute(query, tuple(params))
        products = cursor.fetchall()
        if "user_id" in session and (search or category_id.isdigit()):
            log_activity(
                session["user_id"],
                "product_search",
                {"search": search, "category_id": category_id or None}
            )
        cursor.execute("SELECT * FROM categories ORDER BY category_name")
        categories = cursor.fetchall()

        return render_template(
            "products.html",
            products=products,
            categories=categories,
            search=search,
            selected_category=category_id
        )
    except Error as error:
        app.logger.exception("Products page database error: %s", error)
        return "Unable to load products.", 500
    finally:
        close_db(cursor, connection)


@app.route("/product/<int:product_id>")
def product_details(product_id):
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("""
            SELECT p.*, c.category_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            WHERE p.product_id = %s
        """, (product_id,))
        product = cursor.fetchone()
        if product is None:
            return "Product not found", 404
        if "user_id" in session:
            log_activity(
                session["user_id"],
                "product_view",
                {"product_id": product_id, "product_name": product["product_name"]}
            )
        return render_template("product_details.html", product=product)
    except Error as error:
        app.logger.exception("Product details database error: %s", error)
        return "Unable to load this product.", 500
    finally:
        close_db(cursor, connection)


# ==========================================================
# 4. USER REGISTRATION, LOGIN AND LOGOUT
# ==========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not full_name or not email or not password:
            return render_template("register.html", error="Please fill in all required fields.")
        if len(password) < 6:
            return render_template("register.html", error="Password must contain at least 6 characters.")

        connection, cursor, error_response = get_connection_or_error()
        if error_response:
            return error_response
        try:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return render_template("register.html", error="Email already registered!")

            password_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (full_name, email, phone, password_hash)
                VALUES (%s, %s, %s, %s)
            """, (full_name, email, phone or None, password_hash))
            new_user_id = cursor.lastrowid
            connection.commit()
            log_activity(new_user_id, "account_registered", {"email": email})
            return redirect(url_for("login"))
        except IntegrityError:
            connection.rollback()
            return render_template("register.html", error="This email is already registered.")
        except Error as error:
            connection.rollback()
            app.logger.exception("Registration database error: %s", error)
            return "Registration failed. Please try again.", 500
        finally:
            close_db(cursor, connection)
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection, cursor, error_response = get_connection_or_error()
        if error_response:
            return error_response
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["user_id"]
                session["user_name"] = user["full_name"]
                session["role"] = user["role"]
                log_activity(user["user_id"], "login", {"role": user["role"]})
                if user["role"] == "admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("home"))

            return render_template("login.html", error="Invalid email or password!")
        except Error as error:
            app.logger.exception("Login database error: %s", error)
            return "Login failed. Please try again.", 500
        finally:
            close_db(cursor, connection)
    return render_template("login.html")


@app.route("/logout")
def logout():
    if "user_id" in session:
        log_activity(session["user_id"], "logout", {})
    session.clear()
    return redirect(url_for("home"))


# ==========================================================
# 5. CUSTOMER BOOKING SYSTEM
# ==========================================================

@app.route("/book/<int:product_id>", methods=["GET", "POST"])
def book_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response

    try:
        cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        if product is None:
            return "Product not found", 404
        if product["availability_status"] != "available":
            return "This outfit is currently unavailable.", 400
        if request.method == "GET":
            return render_template("booking.html", product=product, today=date.today().isoformat(), error=None)

        try:
            start_date = datetime.strptime(request.form.get("start_date", ""), "%Y-%m-%d").date()
            end_date = datetime.strptime(request.form.get("end_date", ""), "%Y-%m-%d").date()
        except ValueError:
            return render_template("booking.html", product=product,today=date.today().isoformat(), error="Please enter valid rental dates.")

        if start_date < date.today():
            return render_template("booking.html", product=product, today=date.today().isoformat(), error="Start date cannot be in the past.")
        if end_date < start_date:
            return render_template("booking.html", product=product, today=date.today().isoformat(), error="End date must be on or after the start date.")

        rental_days = (end_date - start_date).days + 1
        total_amount = Decimal(str(product["rental_price"])) * rental_days

        try:
            # Lock the product row while checking availability and creating the booking.
            cursor.execute("""
                SELECT availability_status
                FROM products
                WHERE product_id = %s
                FOR UPDATE
            """, (product_id,))
            locked_product = cursor.fetchone()

            if not locked_product or locked_product["availability_status"] != "available":
                connection.rollback()
                return render_template("booking.html", product=product, error="This outfit is currently unavailable.")

            cursor.execute("""
                SELECT COUNT(*) AS booking_count
                FROM bookings b
                JOIN booking_items bi ON b.booking_id = bi.booking_id
                WHERE bi.product_id = %s
                  AND b.booking_status IN ('pending', 'confirmed')
                  AND NOT (b.end_date < %s OR b.start_date > %s)
            """, (product_id, start_date, end_date))
            existing_booking = cursor.fetchone()

            if existing_booking["booking_count"] > 0:
                connection.rollback()
                return render_template(
                    "booking.html",
                    product=product,
                    error="Sorry! This outfit is already booked for the selected dates. Please choose different dates."
                )

            cursor.execute("""
                INSERT INTO bookings (user_id, start_date, end_date, total_amount)
                VALUES (%s, %s, %s, %s)
            """, (session["user_id"], start_date, end_date, total_amount))
            booking_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO booking_items (booking_id, product_id, quantity, rental_price)
                VALUES (%s, %s, %s, %s)
            """, (booking_id, product_id, 1, product["rental_price"]))

            connection.commit()
            log_activity(
                session["user_id"],
                "booking_created",
                {
                    "booking_id": booking_id,
                    "product_id": product_id,
                    "product_name": product["product_name"],
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_amount": str(total_amount)
                }
            )
            return redirect(url_for("my_bookings"))
        except Exception:
            connection.rollback()
            raise

    except Error as error:
        connection.rollback()
        app.logger.exception("Booking database error: %s", error)
        return "Booking failed. Please check the application terminal for details.", 500
    except Exception as error:
        connection.rollback()
        app.logger.exception("Unexpected booking error: %s", error)
        return "Something went wrong while creating your booking.", 500
    finally:
        close_db(cursor, connection)


@app.route("/my-bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("""
            SELECT b.booking_id, b.start_date, b.end_date, b.total_amount,
                   b.booking_status, p.product_name, p.image_url
            FROM bookings b
            JOIN booking_items bi ON b.booking_id = bi.booking_id
            JOIN products p ON bi.product_id = p.product_id
            WHERE b.user_id = %s
            ORDER BY b.booking_date DESC
        """, (session["user_id"],))
        bookings = cursor.fetchall()
        return render_template("my_bookings.html", bookings=bookings)
    except Error as error:
        app.logger.exception("My bookings database error: %s", error)
        return "Unable to load your bookings.", 500
    finally:
        close_db(cursor, connection)


@app.route("/my-activity")
def my_activity():
    """Show the signed-in user's recent activity stored in MongoDB."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    from database.mongo_connection import get_user_activities
    activities = get_user_activities(session["user_id"])
    for activity in activities:
        timestamp = activity.get("timestamp")
        if timestamp is not None:
            activity["timestamp"] = timestamp.isoformat()

    return render_template("my_activity.html", activities=activities)


# ==========================================================
# 6. ADMIN DASHBOARD
# ==========================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("SELECT COUNT(*) AS total_users FROM users")
        total_users = cursor.fetchone()["total_users"]
        cursor.execute("SELECT COUNT(*) AS total_products FROM products")
        total_products = cursor.fetchone()["total_products"]
        cursor.execute("SELECT COUNT(*) AS total_bookings FROM bookings")
        total_bookings = cursor.fetchone()["total_bookings"]
        cursor.execute("""
            SELECT COUNT(*) AS pending_bookings
            FROM bookings WHERE booking_status = 'pending'
        """)
        pending_bookings = cursor.fetchone()["pending_bookings"]

        return render_template(
            "admin/dashboard.html",
            total_users=total_users,
            total_products=total_products,
            total_bookings=total_bookings,
            pending_bookings=pending_bookings
        )
    except Error as error:
        app.logger.exception("Admin dashboard database error: %s", error)
        return "Unable to load the admin dashboard.", 500
    finally:
        close_db(cursor, connection)


# ==========================================================
# 7. ADMIN PRODUCT MANAGEMENT
# ==========================================================

@app.route("/admin/products")
@admin_required
def admin_products():
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("""
            SELECT p.*, c.category_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.product_id DESC
        """)
        products = cursor.fetchall()
        return render_template("admin/products.html", products=products)
    except Error as error:
        app.logger.exception("Admin products database error: %s", error)
        return "Unable to load product management.", 500
    finally:
        close_db(cursor, connection)


@app.route("/admin/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("SELECT * FROM categories ORDER BY category_name")
        categories = cursor.fetchall()

        if request.method == "GET":
            return render_template("admin/add_product.html", categories=categories)

        try:
            product_name = request.form.get("product_name", "").strip()
            category_id = int(request.form.get("category_id", ""))
            description = request.form.get("description", "").strip()
            size = request.form.get("size", "").strip()
            color = request.form.get("color", "").strip()
            rental_price = Decimal(request.form.get("rental_price", ""))
            security_deposit = Decimal(request.form.get("security_deposit", "0"))
            image_url = request.form.get("image_url", "").strip()
            availability_status = request.form.get("availability_status", "available")

            if not product_name or not size or not color or not image_url:
                raise ValueError
            if rental_price <= 0 or security_deposit < 0:
                raise ValueError
            if availability_status not in ("available", "unavailable"):
                raise ValueError
        except (ValueError, InvalidOperation):
            return render_template(
                "admin/add_product.html",
                categories=categories,
                error="Please enter valid product details and prices."
            )

        cursor.execute("""
            INSERT INTO products
                (product_name, category_id, description, size, color,
                 rental_price, security_deposit, image_url, availability_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_name, category_id, description, size, color,
            rental_price, security_deposit, image_url, availability_status
        ))
        connection.commit()
        return redirect(url_for("admin_products"))
    except IntegrityError:
        connection.rollback()
        return "Unable to add product. Please check that the selected category exists.", 400
    except Error as error:
        connection.rollback()
        app.logger.exception("Add product database error: %s", error)
        return "Unable to add product.", 500
    finally:
        close_db(cursor, connection)


@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        if product is None:
            return "Product not found", 404

        cursor.execute("SELECT * FROM categories ORDER BY category_name")
        categories = cursor.fetchall()

        if request.method == "GET":
            return render_template("admin/edit_product.html", product=product, categories=categories)

        try:
            product_name = request.form.get("product_name", "").strip()
            category_id = int(request.form.get("category_id", ""))
            description = request.form.get("description", "").strip()
            size = request.form.get("size", "").strip()
            color = request.form.get("color", "").strip()
            rental_price = Decimal(request.form.get("rental_price", ""))
            security_deposit = Decimal(request.form.get("security_deposit", "0"))
            image_url = request.form.get("image_url", "").strip()
            availability_status = request.form.get("availability_status", "available")

            if not product_name or not size or not color or not image_url:
                raise ValueError
            if rental_price <= 0 or security_deposit < 0:
                raise ValueError
            if availability_status not in ("available", "unavailable"):
                raise ValueError
        except (ValueError, InvalidOperation):
            return render_template(
                "admin/edit_product.html",
                product=product,
                categories=categories,
                error="Please enter valid product details and prices."
            )

        cursor.execute("""
            UPDATE products
            SET product_name = %s, category_id = %s, description = %s,
                size = %s, color = %s, rental_price = %s,
                security_deposit = %s, image_url = %s,
                availability_status = %s
            WHERE product_id = %s
        """, (
            product_name, category_id, description, size, color,
            rental_price, security_deposit, image_url,
            availability_status, product_id
        ))
        connection.commit()
        return redirect(url_for("admin_products"))
    except IntegrityError:
        connection.rollback()
        return "Unable to update product. Please check the selected category.", 400
    except Error as error:
        connection.rollback()
        app.logger.exception("Edit product database error: %s", error)
        return "Unable to update product.", 500
    finally:
        close_db(cursor, connection)


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        if cursor.rowcount == 0:
            connection.rollback()
            return "Product not found.", 404
        connection.commit()
        return redirect(url_for("admin_products"))
    except IntegrityError:
        connection.rollback()
        return (
            "This product cannot be deleted because it is linked to existing "
            "bookings, reviews or wishlist entries. Mark it as unavailable instead."
        ), 409
    except Error as error:
        connection.rollback()
        app.logger.exception("Delete product database error: %s", error)
        return "Unable to delete product.", 500
    finally:
        close_db(cursor, connection)


# ==========================================================
# 8. ADMIN BOOKING MANAGEMENT
# ==========================================================

@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute("""
            SELECT b.booking_id, b.booking_date, b.start_date, b.end_date,
                   b.total_amount, b.booking_status,
                   u.full_name, u.email, p.product_name, p.image_url
            FROM bookings b
            JOIN users u ON b.user_id = u.user_id
            JOIN booking_items bi ON b.booking_id = bi.booking_id
            JOIN products p ON bi.product_id = p.product_id
            ORDER BY b.booking_date DESC
        """)
        bookings = cursor.fetchall()
        return render_template("admin/bookings.html", bookings=bookings)
    except Error as error:
        app.logger.exception("Admin bookings database error: %s", error)
        return "Unable to load booking management.", 500
    finally:
        close_db(cursor, connection)


@app.route("/admin/bookings/update/<int:booking_id>", methods=["POST"])
@admin_required
def update_booking_status(booking_id):
    new_status = request.form.get("booking_status", "").strip()
    allowed_statuses = {"pending", "confirmed", "cancelled", "completed"}
    if new_status not in allowed_statuses:
        return "Invalid booking status.", 400

    connection, cursor, error_response = get_connection_or_error()
    if error_response:
        return error_response
    try:
        cursor.execute(
            "UPDATE bookings SET booking_status = %s WHERE booking_id = %s",
            (new_status, booking_id)
        )
        if cursor.rowcount == 0:
            cursor.execute("SELECT booking_id FROM bookings WHERE booking_id = %s", (booking_id,))
            if cursor.fetchone() is None:
                connection.rollback()
                return "Booking not found.", 404
        connection.commit()
        log_activity(
            session["user_id"],
            "admin_booking_status_updated",
            {"booking_id": booking_id, "new_status": new_status}
        )
        return redirect(url_for("admin_bookings"))
    except Error as error:
        connection.rollback()
        app.logger.exception("Update booking status error: %s", error)
        return "Unable to update booking status.", 500
    finally:
        close_db(cursor, connection)


# ==========================================================
# 9. RUN APPLICATION
# ==========================================================

if __name__ == "__main__":
    import os
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )