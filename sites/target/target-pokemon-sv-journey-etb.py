from target_webbot import *

LOG_FILE = rf"C:\Logs\selenium-webbot\target-pokemon-sv--journey-etb.csv"
PRODUCT_URL = "https://www.target.com/p/2025-pok-233-mon-scarlet-violet-s9-elite-trainer-box/-/A-93803439"

configure_logging(LOG_FILE)
driver = setup_driver()
try:
    sign_in(driver)
    if add_to_cart(driver, PRODUCT_URL):
        if place_order(driver):  # ensure order is placed before retrying
            logging.info("first purchase successful. running a second attempt.")
            time.sleep(5)  # short pause before re-running
            
            if add_to_cart(driver, PRODUCT_URL):
                place_order(driver)
                logging.info("second purchase successful.")
finally:
    driver.quit()
    logging.info("WebDriver session ended.")

