from sams_club_webbot import *
import logging
import os
import time

LOG_FILE = r"C:\Logs\selenium-webbot\sams-club-pokemon-sea-and-sky.csv"
PRODUCT_URL = "https://www.samsclub.com/p/pokemon-crown-zenith-sea-sky-premium-collection/P990345457"

# Configure logging
configure_logging(LOG_FILE)

# Setup driver
driver = setup_driver()

try:
    # Sign in
    try:
        sign_in(driver)
    except Exception as e:
        logging.error(f"Sign-in failed: {e}")
        raise

    # Keep trying until order is placed, with max attempts
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        if add_to_cart(driver, PRODUCT_URL):
            sendStockAlertTextSmtp(PRODUCT_URL)  # Notify when in stock
            if place_order(driver):
                sendOrderPlacedTextSmtp(PRODUCT_URL)  # Notify when ordered
                logging.info("Order placed successfully. Exiting loop.")
                break
        else:
            logging.warning(f"Attempt {attempt + 1}/{max_attempts}: Failed to add item to cart. Retrying...")
            time.sleep(5)
            attempt += 1
    else:
        logging.error("Max attempts reached. Could not place order.")

finally:
    time.sleep()
    driver.quit()
    logging.info("WebDriver session ended.")