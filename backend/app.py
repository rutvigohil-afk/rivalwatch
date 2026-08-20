from flask import Flask, jsonify
from flask_cors import CORS
from database import get_connection, create_tables
from datetime import datetime

import os
import time
import requests
from dotenv import load_dotenv


# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

app = Flask(__name__)
CORS(app)

create_tables()

BRIGHT_DATA_API_TOKEN = os.getenv(
    "BRIGHT_DATA_API_TOKEN"
)

BRIGHT_DATA_COLLECTOR_ID = (
    "c_mt1lrdw314u6wqb0op"
)

BRIGHT_DATA_TARGET_URL = (
    "https://www.ikea.com/in/en/cat/tables-chairs-fu002/"
)

BRIGHT_DATA_API_TOKEN = os.getenv(
    "BRIGHT_DATA_API_TOKEN"
)

BRIGHT_DATA_COLLECTOR_ID = (
    "c_mt1lrdw314u6wqb0op"
)

BRIGHT_DATA_TARGET_URL = (
    "https://www.ikea.com/in/en/cat/tables-chairs-fu002/"
)


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return jsonify({
        "project": "RivalWatch AI",
        "status": "running"
    })


# ==========================================
# HEALTH
# ==========================================

@app.route("/health")
def health():

    return jsonify({
        "status": "healthy"
    })


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/api/dashboard")
def dashboard():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM products"
    )

    product_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM changes"
    )

    change_count = cursor.fetchone()[0]

    # Recent changes
    cursor.execute("""
        SELECT
            product_id,
            change_type,
            old_value,
            new_value,
            percentage,
            detected_at
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


# ==========================================
# PRODUCTS
# ==========================================

@app.route("/api/products")
def products():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            product_id,
            name,
            description,
            price,
            currency,
            rating,
            reviews,
            url,
            scraped_at
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


# ==========================================
# CHANGES
# ==========================================

@app.route("/api/changes")
def changes():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            product_id,
            change_type,
            old_value,
            new_value,
            percentage,
            detected_at
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


# ==========================================
# SAVE SCRAPED PRODUCTS
# ==========================================

def save_products(scraped_products):

    connection = get_connection()
    cursor = connection.cursor()

    changes_detected = 0

    for product in scraped_products:

        product_id = product.get("product_id")

        if not product_id:
            continue

        # Get previous version of product
        cursor.execute("""
            SELECT
                price,
                rating,
                name,
                description
            FROM products
            WHERE product_id = ?
        """, (product_id,))

        old_product = cursor.fetchone()

        now = datetime.now().isoformat()

        # ==========================================
        # NEW PRODUCT
        # ==========================================

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
                product_id,
                product.get("name"),
                product.get("description"),
                product.get("price"),
                product.get("currency"),
                product.get("rating"),
                product.get("reviews"),
                product.get("url"),
                now
            ))

            continue

        # =================================================
        # OLD VALUES
        # =================================================

        old_price = old_product[0]
        old_rating = old_product[1]
        old_name = old_product[2]
        old_description = old_product[3]

        new_price = product.get("price")
        new_rating = product.get("rating")
        new_name = product.get("name")
        new_description = product.get("description")

        # ==========================================
        # PRICE CHANGE
        # ==========================================

        if old_price != new_price:

            percentage = None

            if old_price and new_price:

                percentage = round(
                    (
                        (new_price - old_price)
                        / old_price
                    ) * 100,
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

        # ==========================================
        # RATING CHANGE
        # ==========================================

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

        # ==========================================
        # CONTENT CHANGE
        # ==========================================

        if (
            old_name != new_name
            or old_description != new_description
        ):

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

        # ==========================================
        # UPDATE PRODUCT
        # ==========================================

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


# ==========================================
# BRIGHT DATA SCRAPER
# ==========================================

@app.route("/api/scrape", methods=["POST"])
def run_scraper():

    if not BRIGHT_DATA_API_TOKEN:

        return jsonify({
            "success": False,
            "error": (
                "BRIGHT_DATA_API_TOKEN "
                "is missing from .env"
            )
        }), 500

    try:

        # ==========================================
        # 1. TRIGGER CUSTOM SCRAPER
        # ==========================================

        trigger_url = (
            "https://api.brightdata.com/dca/trigger"
            f"?collector={BRIGHT_DATA_COLLECTOR_ID}"
            "&queue_next=1"
        )

        headers = {
            "Authorization": (
                f"Bearer {BRIGHT_DATA_API_TOKEN}"
            ),
            "Content-Type": "application/json"
        }

        payload = [
            {
                "url": BRIGHT_DATA_TARGET_URL
            }
        ]

        print(
            "\nStarting Bright Data scraper..."
        )

        response = requests.post(
            trigger_url,
            headers=headers,
            json=payload,
            timeout=60
        )

        print(
            "Bright Data trigger:",
            response.status_code
        )

        print(
            "Response:",
            response.text
        )

        response.raise_for_status()

        trigger_result = response.json()

        collection_id = (
            trigger_result.get("collection_id")
        )

        if not collection_id:

            raise Exception(
                "Bright Data did not return "
                f"a collection_id: {trigger_result}"
            )

        print(
            "Collection ID:",
            collection_id
        )

        # ==========================================
        # 2. WAIT FOR DATASET
        # ==========================================

        dataset_url = (
            "https://api.brightdata.com/dca/dataset"
            f"?id={collection_id}"
        )

        scraped_data = None

        for attempt in range(36):

            time.sleep(5)

            result = requests.get(
                dataset_url,
                headers={
                    "Authorization": (
                        f"Bearer {BRIGHT_DATA_API_TOKEN}"
                    )
                },
                timeout=60
            )

            print(
                f"Bright Data attempt "
                f"{attempt + 1}/36:",
                result.status_code
            )

            # ------------------------------------------
            # Dataset not ready
            # ------------------------------------------

            if result.status_code == 202:

                print(
                    "Dataset still processing:",
                    result.text
                )

                continue

            # ------------------------------------------
            # Other error
            # ------------------------------------------

            if result.status_code != 200:

                print(
                    "Bright Data error:",
                    result.text
                )

                continue

            data = result.json()

            # ==========================================
            # COMPLETED RESULT
            # ==========================================

            if (
                isinstance(data, dict)
                and "products" in data
            ):

                scraped_data = data["products"]

                break

            # ==========================================
            # DIRECT LIST RESULT
            # ==========================================

            if isinstance(data, list):

                scraped_data = data

                break

            # ==========================================
            # STATUS RESPONSE
            # ==========================================

            if isinstance(data, dict):

                print(
                    "Bright Data status:",
                    data
                )

                if data.get("status") in [
                    "failed",
                    "error"
                ]:

                    raise Exception(
                        f"Bright Data failed: {data}"
                    )

        # ==========================================
        # TIMEOUT
        # ==========================================

        if scraped_data is None:

            raise Exception(
                "Bright Data did not return "
                "a completed dataset within "
                "the expected time."
            )

        # ==========================================
        # CLEAN PRODUCTS
        # ==========================================

        scraped_products = []

        for product in scraped_data:

            if not isinstance(product, dict):
                continue

            product_id = product.get(
                "product_id"
            )

            if not product_id:
                continue

            scraped_products.append({

                "product_id": str(
                    product_id
                ),

                "name": product.get(
                    "name",
                    ""
                ),

                "description": product.get(
                    "description"
                ),

                "price": product.get(
                    "price"
                ),

                "currency": product.get(
                    "currency",
                    "INR"
                ),

                "rating": product.get(
                    "rating"
                ),

                "reviews": product.get(
                    "reviews"
                ),

                "url": product.get(
                    "url"
                ),

                "availability": product.get(
                    "availability"
                )
            })

        # ==========================================
        # NO PRODUCTS
        # ==========================================

        if not scraped_products:

            raise Exception(
                "Bright Data returned "
                "zero valid products."
            )

        print(
            "Products received:",
            len(scraped_products)
        )

        # ==========================================
        # SAVE + DETECT CHANGES
        # ==========================================

        changes = save_products(
            scraped_products
        )

        # ==========================================
        # SAVE SUCCESSFUL RUN
        # ==========================================

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO scraper_runs
            (
                status,
                products_found,
                error,
                timestamp
            )
            VALUES (?, ?, ?, ?)
        """, (
            "successful",
            len(scraped_products),
            None,
            datetime.now().isoformat()
        ))

        connection.commit()
        connection.close()

        # ==========================================
        # RETURN RESULT
        # ==========================================

        return jsonify({

            "success": True,

            "products_found": len(
                scraped_products
            ),

            "changes_detected": changes,

            "collector_id": (
                BRIGHT_DATA_COLLECTOR_ID
            ),

            "collection_id": collection_id
        })

    except Exception as error:

        print(
            "\nSCRAPER ERROR:",
            str(error)
        )

        # ==========================================
        # SAVE FAILED RUN
        # ==========================================

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO scraper_runs
            (
                status,
                products_found,
                error,
                timestamp
            )
            VALUES (?, ?, ?, ?)
        """, (
            "failed",
            0,
            str(error),
            datetime.now().isoformat()
        ))

        connection.commit()
        connection.close()

        return jsonify({

            "success": False,

            "products_found": 0,

            "changes_detected": 0,

            "error": str(error)

        }), 500


# ==========================================
# SCRAPER HEALTH
# ==========================================

@app.route("/api/scraper-health")
def scraper_health():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            status,
            products_found,
            error,
            timestamp
        FROM scraper_runs
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    connection.close()

    if row is None:

        return jsonify({
            "status": "no_runs",
            "products_found": 0,
            "error": None,
            "timestamp": None
        })

    return jsonify({

        "status": row[0],

        "products_found": row[1],

        "error": row[2],

        "timestamp": row[3]
    })


# ==========================================
# START
# ==========================================

if __name__ == "__main__":


    app.run(
        debug=True,
        port=5000
    )