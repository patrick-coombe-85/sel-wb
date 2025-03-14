from target_webbot import *

LOG_FILE = rf"C:\Logs\selenium-webbot\target-pokemon-swsh-lo-etb.csv"
PRODUCT_URL = "https://www.target.com/p/pokemon-trading-card-game-sword-38-shield-lost-origin-elite-trainer-box/-/A-87154260"

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

