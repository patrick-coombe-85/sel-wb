from target_webbot import *

LOG_FILE = rf"C:\Logs\selenium-webbot\target-pokemon-sv-journey-3-pack-scrafty.csv"
PRODUCT_URL = "https://www.target.com/p/2025-pokemon-scarlet-violet-s9-3pk-bl-version-1/-/A-93859728"

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

