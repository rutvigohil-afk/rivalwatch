from flask import Flask, jsonify
from flask_cors import CORS
from database import get_connection, create_tables
from datetime import datetime

app = Flask(__name__)
CORS(app)

create_tables()


# ===============================
# HOME
# ===============================

@app.route("/")
def home():
    return jsonify({
        "project": "RivalWatch AI",
        "status": "running"
    })


# ===============================
# HEALTH
# ===============================

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


# ===============================
# DASHBOARD
# ===============================

@app.route("/api/dashboard")
def dashboard():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM changes")
    change_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT product_id, change_type, old_value,
               new_value, percentage, detected_at
        FROM changes
        ORDER BY id DESC
        LIMIT 5
    """)

    rows = cursor.fetchall()

    recent_changes = []

    for row in rows:
        recent_changes.append({
            "product_id": row[0],
            "change_type": row[1],
            "old_value": row[2],
            "new_value": row[3],
            "percentage": row[4],
            "detected_at": row[5]
        })

    connection.close()

    return jsonify({
        "product_count": product_count,
        "change_count": change_count,
        "recent_changes": recent_changes
    })


# ===============================
# PRODUCTS
# ===============================

@app.route("/api/products")
def products():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT product_id, name, description,
               price, currency, rating,
               reviews, url, scraped_at
        FROM products
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    result = []

    for row in rows:
        result.append({
            "product_id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "currency": row[4],
            "rating": row[5],
            "reviews": row[6],
            "url": row[7],
            "scraped_at": row[8]
        })

    connection.close()

    return jsonify(result)


# ===============================
# CHANGES
# ===============================

@app.route("/api/changes")
def changes():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT product_id, change_type,
               old_value, new_value,
               percentage, detected_at
        FROM changes
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    result = []

    for row in rows:
        result.append({
            "product_id": row[0],
            "change_type": row[1],
            "old_value": row[2],
            "new_value": row[3],
            "percentage": row[4],
            "detected_at": row[5]
        })

    connection.close()

    return jsonify(result)


# ===============================
# SAVE SCRAPED PRODUCTS
# ===============================

def save_products(scraped_products):

    connection = get_connection()
    cursor = connection.cursor()

    changes_detected = 0

    for product in scraped_products:

        product_id = product["product_id"]

        cursor.execute("""
            SELECT price, rating, name, description
            FROM products
            WHERE product_id = ?
        """, (product_id,))

        old_product = cursor.fetchone()

        now = datetime.now().isoformat()

        # ---------------------------
        # NEW PRODUCT
        # ---------------------------

        if old_product is None:

            cursor.execute("""
                INSERT INTO products
                (
                    product_id,
                    name,
                    description,
                    price,
                    currency,
                    rating,
                    reviews,
                    url,
                    scraped_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product["product_id"],
                product["name"],
                product.get("description"),
                product.get("price"),
                product.get("currency"),
                product.get("rating"),
                product.get("reviews"),
                product.get("url"),
                now
            ))

            continue

        old_price = old_product[0]
        old_rating = old_product[1]
        old_name = old_product[2]
        old_description = old_product[3]

        new_price = product.get("price")
        new_rating = product.get("rating")
        new_name = product.get("name")
        new_description = product.get("description")


        # ---------------------------
        # PRICE CHANGE
        # ---------------------------

        if old_price != new_price:

            percentage = None

            if old_price and new_price:
                percentage = round(
                    ((new_price - old_price) / old_price) * 100,
                    2
                )

            cursor.execute("""
                INSERT INTO changes
                (
                    product_id,
                    change_type,
                    old_value,
                    new_value,
                    percentage,
                    detected_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                "PRICE_CHANGE",
                str(old_price),
                str(new_price),
                percentage,
                now
            ))

            changes_detected += 1


        # ---------------------------
        # RATING CHANGE
        # ---------------------------

        if old_rating != new_rating:

            cursor.execute("""
                INSERT INTO changes
                (
                    product_id,
                    change_type,
                    old_value,
                    new_value,
                    percentage,
                    detected_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                "RATING_CHANGE",
                str(old_rating),
                str(new_rating),
                None,
                now
            ))

            changes_detected += 1


        # ---------------------------
        # NAME / STRUCTURE CHANGE
        # ---------------------------

        if old_name != new_name or old_description != new_description:

            cursor.execute("""
                INSERT INTO changes
                (
                    product_id,
                    change_type,
                    old_value,
                    new_value,
                    percentage,
                    detected_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                "CONTENT_CHANGE",
                str(old_name),
                str(new_name),
                None,
                now
            ))

            changes_detected += 1


        # ---------------------------
        # UPDATE PRODUCT
        # ---------------------------

        cursor.execute("""
            UPDATE products
            SET
                name = ?,
                description = ?,
                price = ?,
                currency = ?,
                rating = ?,
                reviews = ?,
                url = ?,
                scraped_at = ?
            WHERE product_id = ?
        """, (
            new_name,
            new_description,
            new_price,
            product.get("currency"),
            new_rating,
            product.get("reviews"),
            product.get("url"),
            now,
            product_id
        ))


    connection.commit()
    connection.close()

    return changes_detected


# ===============================
# SCRAPER
# ===============================

@app.route("/api/scrape", methods=["POST"])
def run_scraper():

    # TEST DATA
    # This represents the data returned by Bright Data.

    scraped_products = [
        {
            "product_id": "90369550",
            "name": "NORDVIKEN",
            "description": "Chair, white",
            "price": 4990,
            "currency": "INR",
            "rating": 4.3,
            "reviews": 517,
            "url": "https://www.ikea.com/in/en/p/nordviken-chair-white-90369550/"
        },

        {
            "product_id": "40559755",
            "name": "GRÖNSTA",
            "description": "Chair with armrests, in/outdoor, white",
            "price": 6950,
            "currency": "INR",
            "rating": 4.6,
            "reviews": 100,
            "url": "https://www.ikea.com/in/en/p/groensta-chair-with-armrests-in-outdoor-white-40559755/"
        },

        {
            "product_id": "60349672",
            "name": "TOBIAS",
            "description": "Chair, transparent/chrome-plated",
            "price": 7950,
            "currency": "INR",
            "rating": 3.9,
            "reviews": 200,
            "url": "https://www.ikea.com/in/en/p/tobias-chair-transparent-chrome-plated-60349672/"
        }
    ]

    changes = save_products(scraped_products)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO scraper_runs
        (status, products_found, error, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        "successful",
        len(scraped_products),
        None,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "products_found": len(scraped_products),
        "changes_detected": changes
    })


# ===============================
# START
# ===============================

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000
    )