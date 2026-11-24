CREATE DATABASE rentwear_db;
USE rentwear_db;
SELECT DATABASE();

USE rentwear_db;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    address TEXT,
    role ENUM('customer', 'admin') DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
SHOW TABLES;
DESCRIBE users;

USE rentwear_db;

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);
SHOW TABLES;
DESCRIBE categories;

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    description TEXT,
    size VARCHAR(10),
    color VARCHAR(50),
    rental_price DECIMAL(10,2) NOT NULL,
    security_deposit DECIMAL(10,2) DEFAULT 0.00,
    image_url VARCHAR(255),
    availability_status ENUM('available', 'unavailable')
        DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id)
    REFERENCES categories(category_id)
);
SHOW TABLES;
DESCRIBE products;

SHOW CREATE TABLE products;
SHOW TABLES;

USE rentwear_db;

CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    booking_status ENUM(
        'pending',
        'confirmed',
        'cancelled',
        'completed'
    ) DEFAULT 'pending',

    FOREIGN KEY (user_id)
    REFERENCES users(user_id),

    CHECK (end_date >= start_date),
    CHECK (total_amount >= 0)
);

CREATE TABLE booking_items (
    booking_item_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1,
    rental_price DECIMAL(10,2) NOT NULL,

    FOREIGN KEY (booking_id)
    REFERENCES bookings(booking_id),

    FOREIGN KEY (product_id)
    REFERENCES products(product_id),

    CHECK (quantity > 0),
    CHECK (rental_price >= 0)
);
SHOW TABLES;
DESCRIBE bookings;
DESCRIBE booking_items;

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method ENUM(
        'UPI',
        'Card',
        'Net Banking',
        'Cash'
    ) NOT NULL,
    payment_status ENUM(
        'pending',
        'completed',
        'failed',
        'refunded'
    ) DEFAULT 'pending',
    transaction_id VARCHAR(100) UNIQUE,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (booking_id)
    REFERENCES bookings(booking_id),

    CHECK (amount >= 0)
);
DESCRIBE payments;

CREATE TABLE rental_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_item_id INT NOT NULL,
    pickup_date DATE,
    return_date DATE,
    rental_status ENUM(
        'upcoming',
        'rented',
        'returned',
        'overdue'
    ) DEFAULT 'upcoming',
    condition_notes TEXT,

    FOREIGN KEY (booking_item_id)
    REFERENCES booking_items(booking_item_id),

    CHECK (
        return_date IS NULL
        OR pickup_date IS NULL
        OR return_date >= pickup_date
    )
);
CREATE TABLE reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    rating INT NOT NULL,
    review_text TEXT,
    review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(user_id),

    FOREIGN KEY (product_id)
    REFERENCES products(product_id),

    CHECK (rating BETWEEN 1 AND 5),

    UNIQUE (user_id, product_id)
);

CREATE TABLE wishlist (
    wishlist_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)
        REFERENCES users (user_id),
    FOREIGN KEY (product_id)
        REFERENCES products (product_id),
    UNIQUE (user_id , product_id)
);
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INT,
    action_details TEXT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(user_id)
    ON DELETE SET NULL
);
SHOW TABLES;

USE rentwear_db;

INSERT INTO categories (category_name, description)
VALUES
('Wedding Wear', 'Designer outfits for weddings'),
('Festive Wear', 'Traditional outfits for festivals'),
('Party Wear', 'Stylish outfits for parties'),
('Western Wear', 'Modern western clothing'),
('Accessories', 'Fashion accessories for rental');

SELECT *FROM categories;

INSERT INTO products
(category_id, product_name, description, size, color,
 rental_price, security_deposit, image_url)
VALUES
(1, 'Red Bridal Lehenga', 'Heavy embroidered bridal lehenga',
 'M', 'Red', 2500, 3000, 'images/lehenga.jpg'),
 
(1, 'Designer Silk Saree', 'Traditional designer silk saree',
 'Free', 'Pink', 1200, 1500, 'images/saree.jpg'),

(2, 'Anarkali Suit', 'Elegant festive Anarkali suit',
 'M', 'Blue', 900, 1000, 'images/anarkali.jpg'),

(3, 'Party Wear Gown', 'Elegant evening party gown',
 'S', 'Black', 1500, 2000, 'images/gown.jpg'),

(1, 'Mens Sherwani', 'Traditional wedding sherwani',
 'L', 'Cream', 2000, 2500, 'images/sherwani.jpg');
 
SELECT * FROM categories;
SELECT * FROM products;
USE rentwear_db;

SELECT product_id, product_name, image_url
FROM products;