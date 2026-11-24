# RentWear – Fashion Rental Marketplace

**Rent Your Style, Not Your Budget.**

RentWear is a web-based clothing rental marketplace that allows customers to explore, rent and manage outfits for different occasions. It provides an affordable and convenient alternative to purchasing expensive outfits for one-time events.

## Project Objectives

- Provide an online platform for renting outfits.
- Allow customers to browse and search clothing collections.
- Enable customers to register, log in and manage bookings.
- Prevent overlapping bookings for the same outfit.
- Provide administrators with product and booking management.
- Use relational and NoSQL databases to manage structured data and customer activity.

## Technology Stack

| Technology | Purpose |
|---|---|
| HTML | Webpage structure |
| CSS | Styling and layout |
| JavaScript | Frontend interactions |
| Python | Backend programming |
| Flask | Web framework |
| MySQL | Relational database |
| MongoDB | Customer activity storage |
| PyMongo | Python-MongoDB connectivity |
| MySQL Workbench | Database design and SQL execution |
| Git and GitHub | Version control and project hosting |

## Main Features

### Customer Module
- User registration and login.
- Browse clothing collections.
- Search available outfits.
- View product details and rental prices.
- Select rental dates and create bookings.
- View personal booking history.
- View recorded customer activities.

### Admin Module
- Admin dashboard.
- Add and manage products.
- Edit product information.
- Delete products.
- View customer bookings.
- Update booking status.

### Database Features
- Relational database with primary and foreign keys.
- SQL joins, views and aggregate queries.
- Stored procedures and triggers.
- Transaction-based booking operations.
- MongoDB collection for customer activity records.

## Database Design

### MySQL Database: `rentwear_db`

The relational database contains the following main tables:

- users
- categories
- products
- bookings
- booking_items
- payments
- rental_history
- reviews
- wishlist
- audit_logs

### MongoDB Database: `rentwear_mongo`

Collection:

- `customer_activities`

This collection stores customer activity records such as login, product views, searches and booking events.

## Project Structure

```text
RentWear/
│
├── app.py
├── config.py
├── requirements.txt
├── .env
├── .env.example
│
├── database/
│   ├── db_connection.py
│   ├── mongo_connection.py
│   ├── schema.sql
│   ├── seed.sql
│   └── advanced_features.sql
│
├── templates/
│   ├── admin/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── products.html
│   ├── product_details.html
│   ├── booking.html
│   ├── my_bookings.html
│   └── my_activity.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── utils/
    └── helpers.py
```

## Installation and Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create the MySQL database using `database/schema.sql`.
5. Insert sample data using `database/seed.sql`.
6. Execute `database/advanced_features.sql` in MySQL Workbench.
7. Ensure the MongoDB server is running.
8. Configure database credentials in `.env`.
9. Start the Flask application:

```bash
python app.py
```

10. Open the application at:

```text
http://127.0.0.1:5000
```

## Environment Variables

Configure the following variables in your local `.env` file:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=rentwear_db

MONGO_URI=mongodb://127.0.0.1:27017/

SECRET_KEY=your_secret_key
```

Never upload your actual `.env` file or database passwords to GitHub.

## Future Enhancements

- Online payment gateway integration.
- Outfit recommendations.
- Advanced filtering by size, category and occasion.
- Rental return tracking.
- Customer reviews and ratings.
- Cloud deployment and production database hosting.

## Project Conclusion

RentWear demonstrates the integration of web development, Python backend programming, relational database management and NoSQL database technology to develop a practical clothing rental marketplace.