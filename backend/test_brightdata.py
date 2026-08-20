import os
import time
import json
import requests
from dotenv import load_dotenv


# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

API_TOKEN = os.getenv("BRIGHT_DATA_API_TOKEN")

COLLECTOR_ID = "c_mt1lrdw314u6wqb0op"

TARGET_URL = "https://www.ikea.com/in/en/cat/tables-chairs-fu002/"


if not API_TOKEN:
    raise Exception(
        "BRIGHT_DATA_API_TOKEN is missing from .env"
    )


# ==========================================
# 1. TRIGGER CUSTOM SCRAPER
# ==========================================

trigger_url = (
    "https://api.brightdata.com/dca/trigger"
    f"?collector={COLLECTOR_ID}&queue_next=1"
)

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

payload = [
    {
        "url": TARGET_URL
    }
]


print("Starting RivalWatch Bright Data scraper...")
print("Collector:", COLLECTOR_ID)


response = requests.post(
    trigger_url,
    headers=headers,
    json=payload,
    timeout=60
)


print("\nTrigger status:", response.status_code)
print("Trigger response:", response.text)


response.raise_for_status()


trigger_result = response.json()

collection_id = trigger_result.get("collection_id")


if not collection_id:
    raise Exception(
        f"Bright Data did not return collection_id: {trigger_result}"
    )


print("\nCollection ID:", collection_id)


# ==========================================
# 2. POLL FOR RESULTS
# ==========================================

dataset_url = (
    "https://api.brightdata.com/dca/dataset"
    f"?id={collection_id}"
)


print("\nWaiting for results...")


for attempt in range(36):

    time.sleep(5)

    result = requests.get(
        dataset_url,
        headers={
            "Authorization": f"Bearer {API_TOKEN}"
        },
        timeout=60
    )


    print(
        f"Attempt {attempt + 1}/36 "
        f"Status: {result.status_code}"
    )


    # ------------------------------------------
    # Still processing / temporary response
    # ------------------------------------------

    if result.status_code != 200:

        print(result.text[:500])

        continue


    data = result.json()


    # ==========================================
    # COMPLETED SCRAPER RESULT
    # ==========================================

    if isinstance(data, dict) and "products" in data:

        products = data["products"]


        # Remove empty objects returned by scraper
        products = [
            product
            for product in products
            if isinstance(product, dict)
            and product.get("product_id")
        ]


        print("\n================================")
        print("SUCCESS!")
        print("================================")


        print("Products:", len(products))


        # ------------------------------------------
        # Display first 5 products
        # ------------------------------------------

        print("\nFirst products:\n")


        for product in products[:5]:

            print(
                product.get("product_id"),
                "|",
                product.get("name"),
                "| Rs.",
                product.get("price")
            )


        # ==========================================
        # SAVE CLEAN RESULT
        # ==========================================

        output_file = "brightdata_result.json"


        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                products,
                file,
                indent=2,
                ensure_ascii=False
            )


        print("\nSaved clean products to:")

        print(output_file)


        # Finished successfully
        break


    # ==========================================
    # STILL PROCESSING
    # ==========================================

    if isinstance(data, dict):

        print("Status:", data)


        if data.get("status") in [
            "failed",
            "error"
        ]:

            raise Exception(
                f"Scraper failed: {data}"
            )


        continue


    # ==========================================
    # UNEXPECTED LIST RESPONSE
    # ==========================================

    if isinstance(data, list):

        products = [
            product
            for product in data
            if isinstance(product, dict)
            and product.get("product_id")
        ]


        print("\n================================")
        print("SUCCESS!")
        print("================================")


        print("Products:", len(products))


        with open(
            "brightdata_result.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                products,
                file,
                indent=2,
                ensure_ascii=False
            )


        print(
            "\nSaved clean products to:"
            " brightdata_result.json"
        )


        break


else:

    raise Exception(
        "Bright Data did not finish within 3 minutes."
    )