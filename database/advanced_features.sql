USE rentwear_db;
CREATE INDEX idx_products_category
ON products(category_id);

CREATE INDEX idx_bookings_user
ON bookings(user_id);

CREATE INDEX idx_bookings_dates
ON bookings(start_date, end_date);
CREATE INDEX idx_booking_items_product
ON booking_items(product_id);

CREATE INDEX idx_reviews_product
ON reviews(product_id);


CREATE OR REPLACE VIEW vw_product_catalog AS
SELECT
    p.product_id,
    p.product_name,
    c.category_name,
    p.size,
    p.color,
    p.rental_price,
    p.security_deposit,
    p.image_url,
    p.availability_status
FROM products p
JOIN categories c
ON p.category_id = c.category_id;


CREATE OR REPLACE VIEW vw_booking_details AS
SELECT
    b.booking_id,
    u.full_name,
    u.email,
    p.product_name,
    b.start_date,
    b.end_date,
    b.total_amount,
    b.booking_status
FROM bookings b
JOIN users u
ON b.user_id = u.user_id
JOIN booking_items bi
ON b.booking_id = bi.booking_id
JOIN products p
ON bi.product_id = p.product_id;


CREATE OR REPLACE VIEW vw_customer_booking_summary AS
SELECT
    u.user_id,
    u.full_name,
    COUNT(b.booking_id) AS total_bookings,
    COALESCE(SUM(b.total_amount), 0) AS total_rental_amount
FROM users u
LEFT JOIN bookings b
ON u.user_id = b.user_id
GROUP BY u.user_id, u.full_name;



USE rentwear_db;

DROP TRIGGER IF EXISTS trg_booking_insert;

DELIMITER //

CREATE TRIGGER trg_booking_insert
AFTER INSERT ON bookings
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs
    (
        user_id,
        action_type,
        table_name,
        record_id,
        action_details
    )
    VALUES
    (
        NEW.user_id,
        'INSERT',
        'bookings',
        NEW.booking_id,
        CONCAT('New booking created. Total amount: ', NEW.total_amount)
    );
END //

DELIMITER ;



-- ==========================================
-- 6. TRIGGER: BOOKING STATUS UPDATE AUDIT
-- ==========================================

DROP TRIGGER IF EXISTS trg_booking_update;

DELIMITER //

CREATE TRIGGER trg_booking_update
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF OLD.booking_status <> NEW.booking_status THEN

        INSERT INTO audit_logs
        (
            user_id,
            action_type,
            table_name,
            record_id,
            action_details
        )
        VALUES
        (
            NEW.user_id,
            'UPDATE',
            'bookings',
            NEW.booking_id,
            CONCAT(
                'Booking status changed from ',
                OLD.booking_status,
                ' to ',
                NEW.booking_status
            )
        );

    END IF;
END //

DELIMITER ;


-- ==========================================
-- 7. STORED PROCEDURE: CUSTOMER BOOKINGS
-- ==========================================

DROP PROCEDURE IF EXISTS sp_customer_bookings;

DELIMITER //

CREATE PROCEDURE sp_customer_bookings(
    IN p_user_id INT
)
BEGIN

    SELECT *
    FROM vw_booking_details
    WHERE booking_id IN
    (
        SELECT booking_id
        FROM bookings
        WHERE user_id = p_user_id
    );

END //

DELIMITER ;


-- ==========================================
-- 8. STORED PROCEDURE: REVENUE REPORT
-- ==========================================

DROP PROCEDURE IF EXISTS sp_revenue_report;

DELIMITER //

CREATE PROCEDURE sp_revenue_report()
BEGIN

    SELECT
        COUNT(*) AS total_bookings,
        COALESCE(SUM(total_amount), 0) AS total_booking_amount,
        COALESCE(AVG(total_amount), 0) AS average_booking_amount
    FROM bookings
    WHERE booking_status IN ('confirmed', 'completed');

END //

DELIMITER ;


-- ==========================================
-- 9. TEST THE VIEWS
-- ==========================================

SELECT * FROM vw_product_catalog;

SELECT * FROM vw_booking_details;

SELECT * FROM vw_customer_booking_summary;


-- ==========================================
-- 10. TEST THE STORED PROCEDURES
-- ==========================================

CALL sp_customer_bookings(1);

CALL sp_revenue_report();


-- ==========================================
-- 11. CHECK AUDIT LOGS
-- ==========================================

SELECT * FROM audit_logs
ORDER BY action_time DESC;

SHOW TRIGGERS;

USE rentwear_db;

SELECT *
FROM audit_logs
ORDER BY action_time DESC;