import sys
import os
import time
import logging
import smtplib
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Credentials
USERNAME = config.TARGET_USERNAME
PASSWORD = config.TARGET_PASSWORD
EMAIL_SENDER = config.SMTP_EMAIL_SENDER
EMAIL_PASSWORD = config.SMTP_EMAIL_PASSWORD

# Configure Logging
def configure_logging(log_file_path):
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format='%(asctime)s,%(levelname)s,%(message)s'
    )

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

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

        try:
            password_input = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            password_input.send_keys(PASSWORD)
            logging.info("Password field was visible immediately. Entered password.")

            submit_button = driver.find_element(By.ID, "login")
            submit_button.click()
            logging.info("Clicked login.")
        except:
            logging.info("Password field not yet available. Clicking next/continue button.")

            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "login"))
            )
            submit_button.click()
            logging.info("Submitted username. Waiting for password...")

            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            password_input.send_keys(PASSWORD)
            logging.info("Entered password.")

            final_submit = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "login"))
            )
            final_submit.click()
            logging.info("Clicked login.")

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='@web/AccountLink']"))
        )
        logging.info("Login successful and confirmed.")
        time.sleep(5)

    except Exception as e:
        logging.error(f"Error signing in: {e}")

def add_to_cart(driver, product_url, click_count=5):
    driver.get(product_url)
    logging.info(f"Opened product page: {product_url}")
    is_refreshing = False

    while True:
        try:
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
                continue
            except:
                logging.info("Item appears to be in stock. Attempting to add to cart.")
                is_refreshing = False

            while True:
                element = WebDriverWait(driver, 6).until(EC.any_of(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='custom-quantity-picker']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='preorderButton']")),
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='fulfillment-cell-shipping']"))
                ))

                if element.get_attribute("data-test") == "custom-quantity-picker":
                    logging.info("Item already in cart. Proceeding to checkout.")
                    return True
                elif element.get_attribute("data-test") == "fulfillment-cell-shipping":
                    try:
                        shipping_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='fulfillment-cell-shipping']"))
                        )
                        shipping_button.click()
                        logging.info("Selected shipping fulfillment option.")
                    except Exception as e:
                        logging.warning(f"Could not select shipping option: {e}")

                try:
                    quantity_select = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[class*='selectCustomButton']"))
                    )
                    quantity_select.click()
                    logging.info("Opened quantity dropdown.")

                    quantity_options = WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[aria-label]"))
                    )
                    if quantity_options:
                        max_quantity_option = quantity_options[-1]
                        max_quantity_option.click()
                        logging.info(f"Selected max quantity: {max_quantity_option.get_attribute('aria-label')}")
                except Exception as e:
                    logging.warning(f"Could not select quantity. Defaulting to 1. Error: {e}")

                while True:
                    try:
                        element = WebDriverWait(driver, 10).until(EC.any_of(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='shippingButton']")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='preorderButton']"))
                        ))

                        for i in range(click_count):
                            element.click()
                        logging.info(f"Clicked Add to Cart button {click_count} times.")

                        popup_close_button = WebDriverWait(driver, 1.5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']"))
                        )

                        if popup_close_button:
                            try:
                                driver.find_element(By.XPATH, "//span[contains(text(), 'Added to cart')]")
                                logging.info("Item successfully added to cart.")
                                return True
                            except:
                                pass

                            popup_close_button.click()
                            logging.info("Closed popup. Retrying Add to Cart.")
                            continue

                    except Exception as e:
                        logging.warning(f"Add to Cart attempt failed or popup not shown: {e}")
                    finally:
                        logging.warning("Add to Cart did not complete successfully. Retrying.")
                        time.sleep(0.1)

        except Exception as e:
            logging.error(f"Error adding item to cart: {e}")
            time.sleep(3)

def fill_cvv_if_popup(driver):
    logging.info("Checking if popup contains CVV input.")
    try:
        popup = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog']"))
        )

        # Try focusing and tabbing to find a CVV/security code field
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(10):
            active = driver.switch_to.active_element
            attr = " ".join([
                active.get_attribute(attr) or ""
                for attr in ["name", "id", "placeholder", "aria-label"]
            ]).lower()

            if any(keyword in attr for keyword in ["cvv", "security code", "card verification"]):
                active.send_keys("123")  # Enter dummy CVV
                logging.info("Filled CVV.")
                body.send_keys(Keys.TAB)  # Move to submit button
                time.sleep(0.2)
                driver.switch_to.active_element.click()
                logging.info("Clicked button after CVV input.")
                return True

            body.send_keys(Keys.TAB)
            time.sleep(0.2)
    except Exception as e:
        logging.info("No popup or CVV field detected.")
    return False

def place_order(driver):
    logging.info("place_order() started.")
    driver.get("https://www.target.com/checkout")
    time.sleep(1)

    while True:
        try:
            place_order_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='placeOrderButton']"))
            )
            place_order_button.click()
            logging.info("Clicked Place Order button.")

            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Thanks for your order!')]"))
                )
                logging.info("Order placed successfully!")
                return True
            except:
                logging.warning("Order confirmation not found. Checking for popup...")

            if fill_cvv_if_popup(driver):
                logging.info("Handled CVV popup. Retrying Place Order.")
                continue

            try:
                popup_close = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']"))
                )
                popup_close.click()
                logging.info("Closed non-CVV popup. Retrying.")
                time.sleep(1)
                continue
            except:
                logging.info("No popup to close.")

            logging.warning("Retrying Place Order...")
            time.sleep(2)

        except Exception as e:
            logging.error(f"Error while placing the order: {e}")
            time.sleep(2)

def sendStockAlertTextSmtp(product_url):
    recipients = ["12178369806@tmomail.net", "12178010309@tmomail.net", "12174167242@txt.att.net"]
    message = f"Target drop live! {product_url}"
    subject = "Target Alert"
    full_email = f"Subject: {subject}\n\n{message}"
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, recipients, full_email)
        server.quit()
        logging.info("Sent alert text.")
    except Exception as e:
        logging.error(f"Failed to send alert text: {e}")

# def main(product_url, log_file):
    # configure_logging(log_file)
    # driver = setup_driver()
    # try:
        # sign_in(driver)
        # if add_to_cart(driver, product_url):
            # sendStockAlertTextSmtp(product_url)
            # place_order(driver)
        # else:
            # logging.warning("Could not add to cart.")
    # finally:
        # driver.quit()
        # logging.info("Driver closed.")

# if __name__ == "__main__":
    # if len(sys.argv) < 3:
        # print("Usage: python targetbot.py [product_url] [log_file_path]")
        # sys.exit(1)

    # url = sys.argv[1]
    # log_path = sys.argv[2]
    # main(url, log_path)
