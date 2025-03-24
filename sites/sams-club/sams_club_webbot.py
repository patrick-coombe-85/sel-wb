import time
import logging
import smtplib
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Credentials (ensure config.py has these defined)
USERNAME = config.SAMS_USERNAME
PASSWORD = config.SAMS_PASSWORD
EMAIL_SENDER = config.SMTP_EMAIL_SENDER
EMAIL_PASSWORD = config.SMTP_EMAIL_PASSWORD

# Configure Logging
def configure_logging(log_file_path):
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format='%(asctime)s,%(levelname)s,%(message)s'
    )

# Setup WebDriver
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")  # Anti-bot detection
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# Sign-in Function
def sign_in(driver):
    try:
        driver.get("https://www.samsclub.com/login")
        logging.info("Opened Sam's Club login page.")

        time.sleep(0.5)  # Small delay for page load

        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.send_keys(USERNAME)
        logging.info("Entered username.")

        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys(PASSWORD)
        logging.info("Entered password.")

        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        logging.info("Clicked sign-in button.")

        time.sleep(5)  # Wait for login to process

        shipping_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span.sc-header-account-button-name[aria-label='Your account']"))
        )
        logging.info("Login successful and confirmed.")

        time.sleep(3)  # Additional buffer

    except Exception as e:
        logging.error(f"Error signing in: {e}")
        raise  # Re-raise to stop execution if login fails

# Add to Cart Function
def add_to_cart(driver, product_url):
    global is_refreshing  # Declare as global to modify it
    is_refreshing = False

    driver.get(product_url)
    logging.info(f"Opened product page: {product_url}")

    while True:
        try:
            # Check if the item is out of stock
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-pc-in-stock-alert"))
                )
                if not is_refreshing:
                    logging.info("Item is out of stock. Refreshing every 20 seconds...")
                    is_refreshing = True
                time.sleep(20)
                driver.refresh()
                continue
            except:
                logging.info("Item appears to be in stock. Attempting to add to cart.")
                is_refreshing = False

            # Attempt to add to cart
            while True:
                element = WebDriverWait(driver, 6).until(EC.any_of(
                    EC.element_to_be_clickable((By.ID, "add-to-cart-input-new-stepper")),  # Already in cart
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.sc-pc-add-to-cart[type='submit']"))  # Add to cart
                ))

                # Case 1: Item already in cart
                if element.get_attribute("id") == "add-to-cart-input-new-stepper":
                    logging.info("Item already in cart. Proceeding to checkout.")
                    return True

                # Select max quantity if available
                try:
                    quantity_select = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-controls='item-quantity']"))
                    )
                    quantity_select.click()
                    logging.info("Opened quantity dropdown.")

                    quantity_options = WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.bst-select-option[aria-label]"))
                    )
                    if quantity_options:
                        max_quantity_option = quantity_options[-1]
                        max_quantity_option.click()
                        logging.info(f"Selected max quantity: {max_quantity_option.get_attribute('aria-label')}")
                except Exception as e:
                    logging.warning(f"Could not select quantity. Defaulting to 1. Error: {e}")

                # Click "Add to Cart"
                element.click()
                logging.info("Clicked Add to Cart button.")

                # Check for success confirmation
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-modal-content div.sc-add-to-cart div.sc-product-added"))
                    )
                    logging.info("Item successfully added to cart.")
                    return True
                except:
                    logging.warning("No confirmation message found. Checking for high-demand popup.")

                # Handle high-demand popup
                try:
                    high_demand_popup = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']"))
                    )
                    high_demand_popup.click()
                    logging.info("Closed high-demand popup. Retrying Add to Cart.")
                    time.sleep(2)
                    continue
                except:
                    logging.info("No high-demand popup detected. Retrying Add to Cart.")
                    time.sleep(3)

        except Exception as e:
            logging.error(f"Error adding item to cart: {e}")
            time.sleep(3)
            driver.refresh()  # Refresh on failure

# Place Order Function
def place_order(driver):
    logging.info("place_order() started.")
    driver.get("https://www.samsclub.com/cart")
    time.sleep(1)

    while True:
        try:
            # Click "Begin Checkout" button
            try:
                begin_checkout_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.sc-cart-order-summary-checkout button"))
                )
                begin_checkout_button.click()
                logging.info("Clicked Begin Checkout button.")
                time.sleep(0.75)
            except:
                logging.warning("Clicking Begin Checkout button failed. Retrying.")

            # Check for "Did you forget?" or "Place Order"
            element2 = WebDriverWait(driver, 10).until(EC.any_of(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.sc-cart-did-you-forget-subHeader button")),  # Did you forget?
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.sc-order-summary button"))  # Place Order
            ))

            element_text = element2.text.strip().lower()
            if element_text != "place order":
                element2.click()
                logging.info("Clicked 'Did you forget?' button to proceed.")
                time.sleep(1)

            # Attempt to place order
            while True:
                place_order_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.sc-order-summary button"))
                )
                place_order_button.click()
                logging.info("Clicked Place Order button.")

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-thank-you-order-summary"))
                    )
                    logging.info("Order successfully placed.")
                    return True
                except:
                    # Handle popup
                    try:
                        popup_close_button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']"))
                        )
                        popup_close_button.click()
                        logging.info("Closed popup. Retrying Place Order.")
                        time.sleep(0.5)
                        continue
                    except:
                        logging.warning("No popup detected. Retrying Place Order.")
                        time.sleep(1)
                        continue

        except Exception as e:
            logging.error(f"Error while placing the order: {e}")
            time.sleep(2)
            continue

# SMTP Functions (unchanged but fixed indentation)
def sendStockAlertTextSmtp(product_url):
    recipients = ["12178369806@tmomail.net", "12178010309@tmomail.net", "12174167242@txt.att.net"]
    message = f"Sam's Club Stock Alert: {product_url}"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            for recipient in recipients:
                server.sendmail(EMAIL_SENDER, recipient, message)
        logging.info("Stock alert email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send stock alert email: {e}")

def sendOrderPlacedTextSmtp(product_url):
    recipients = ["12178369806@tmomail.net", "12178010309@tmomail.net"]
    message = f"Order Placed: {product_url}"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            for recipient in recipients:
                server.sendmail(EMAIL_SENDER, recipient, message)
        logging.info("Order placed email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send order placed email: {e}")