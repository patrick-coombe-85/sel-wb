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

# Credentials
USERNAME = config.TARGET_USERNAME
PASSWORD = config.TARGET_PASSWORD
EMAIL_SENDER = config.SMTP_EMAIL_SENDER
EMAIL_PASSWORD = config.SMTP_EMAIL_PASSWORD

global is_refreshing

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
        driver.get("https://www.target.com")
        logging.info("Opened Target homepage.")

        account_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "account-sign-in"))
        )
        account_link.click()
        logging.info("Clicked Account Sign-in link.")
        time.sleep(0.5)

        sign_in_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='accountNav-signIn']"))
        )
        sign_in_button.click()
        logging.info("Clicked Sign-in button.")
        
        time.sleep(0.5)

        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        email_input.send_keys(USERNAME)
        logging.info("Entered username.")

        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys(PASSWORD)
        logging.info("Entered password.")

        submit_button = driver.find_element(By.ID, "login")
        submit_button.click()
        logging.info("Signed in successfully.")
        
        shipping_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='@web/AccountLink']"))
        )
        logging.info("Login successful and confirmed.")
        
        # sleep for extra time to ensure logged in
        time.sleep(5);
        
    except Exception as e:
        logging.error(f"Error signing in: {e}")
 
def add_to_cart(driver, product_url):
    driver.get(product_url)
    logging.info(f"Opened product page: {product_url}")
    
    is_refreshing = False

    while True:
        try:
            # Check if the item is out of stock
            try:
                element = WebDriverWait(driver, 5).until(EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='notifyMe']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='preorderButtonDisabled']"))
                ))
                if not is_refreshing:
                    logging.info("Item is out of stock. Refreshing every 25 seconds...")
                    is_refreshing = True
                time.sleep(25)
                driver.refresh()
                continue  # Restart loop
            except:
                logging.info("Item appears to be in stock. Attempting to add to cart.")
                is_refreshing = False
                
            sendStockAlertTextSmtp(product_url)

            while True:
            
                # Wait for either "View Cart" or "Shipping Button" (In Stock)
                element = WebDriverWait(driver, 6).until(EC.any_of(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/cart']")),  # View Cart
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='preorderButton']")),
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='fulfillment-cell-shipping']"))  # In Stock
                ))

                # Case 1: "View Cart & Check Out" button is found (Item is already in cart)
                if element.tag_name == "a" and element.get_attribute("href") == "/cart":
                    return True  # Success, move to checkout
                    
                # Case 1: "View Cart & Check Out" button is found (Item is already in cart)
                if element.tag_name == "a" and element.get_attribute("data-test") == "fulfillment-cell-shipping":
                    # Select shipping fulfillment if available
                    try:
                        shipping_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='fulfillment-cell-shipping']"))
                        )
                        shipping_button.click()
                        logging.info("Selected shipping fulfillment option.")
                    except Exception as e:
                        logging.warning(f"Could not select shipping option. It may already be selected. Error: {e}")

                # Select max quantity if available
                try:
                    quantity_select = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[class*='selectCustomButton']"))
                    )
                    quantity_select.click()
                    logging.info("Opened quantity dropdown.")

                    # Find the highest quantity option
                    quantity_options = WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[aria-label]"))
                    )
                    if quantity_options:
                        max_quantity_option = quantity_options[-1]  # Select highest available quantity
                        max_quantity_option.click()
                        logging.info(f"Selected max quantity: {max_quantity_option.get_attribute('aria-label')}")
                except Exception as e:
                    logging.warning(f"Could not select quantity. Defaulting to 1. Error: {e}")

                # Click "Add to Cart"
                add_to_cart_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='shippingButton']"))
                )
                add_to_cart_button.click()
                logging.info("Clicked Add to Cart button.")

                # Check for success confirmation popup
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Added to cart')]"))
                    )
                    logging.info("Item successfully added to cart.")
                    return True  # Success
                except:
                    logging.warning("No confirmation message found. Checking for high-demand popup.")

                # Handle high-demand popup (if it appears)
                try:
                    high_demand_popup = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']"))
                    )
                    high_demand_popup.click()
                    logging.info("Closed high-demand item popup. Retrying Add to Cart.")
                    time.sleep(2)
                    continue  # Restart loop
                except:
                    logging.info("No high-demand popup detected.")

                # If we reach this point and still no confirmation, retry
                logging.warning("Add to Cart did not complete successfully. Retrying.")
                time.sleep(3)

        except Exception as e:
            logging.error(f"Error adding item to cart: {e}")
            time.sleep(3)  # Wait before retrying

def place_order(driver):
    logging.info("place_order() started.")
    driver.get("https://www.target.com/checkout")
    time.sleep(1)  # Allow page to load

    while True:  # Loop until order is placed successfully
        try:
            # Wait for "Place Order" button and click it
            place_order_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='placeOrderButton']"))
            )
            place_order_button.click()
            logging.info("Clicked Place Order button.")

            # Check if order confirmation message appears
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Thanks for your order!')]"))
                )
                logging.info("Order placed successfully!")
                return True  # Exit function if order is successful

            except:
                logging.warning("Order confirmation not found. Checking for popups.")

            # Check for a popup close button and close it if present
            try:
                popup_close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']"))
                )
                popup_close_button.click()
                logging.info("Closed popup. Retrying Place Order.")
                time.sleep(1)  # Short delay before retrying
                continue  # Restart loop

            except:
                logging.info("No popup detected.")

            # If confirmation is still not found, retry placing the order
            logging.warning("Retrying Place Order...")
            time.sleep(2)  # Small delay before retrying

        except Exception as e:
            logging.error(f"Error while placing the order: {e}")
            time.sleep(2)  # Wait before retrying
    
def sendStockAlertTextSmtp(product_url):
    recipients = ["12178369806@tmomail.net", "12178010309@tmomail.net"]

    message = f"Target Stock Alert: {product_url}";

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        for recipient in recipients:
            server.sendmail(EMAIL_SENDER, recipient, message)
            
def sendOrderPlacedTextSmtp(product_url):
    recipients = ["12178369806@tmomail.net", "12178010309@tmomail.net"]

    message = f"Order Placed: {product_url}";

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        for recipient in recipients:
            server.sendmail(EMAIL_SENDER, recipient, message)

# Run the Script
# log_file = rf"C:\Logs\selenium-webbot\target-test.csv"
# configure_logging(log_file)
# driver = setup_driver()
# sign_in(driver)
# add_to_cart(driver, 'https://www.target.com/p/pokemon-scarlet-violet-s3-5-booster-bundle-box/-/A-88897904')
# place_order(driver)