from target_webbot import *

LOG_FILE = rf"C:\Logs\selenium-webbot\target-pokemon-prismatic-tech-slyveon.csv"
PRODUCT_URL = "https://www.target.com/p/2025-pokemon-evolutions-tech-sticker-collection-dw-leafeon/-/A-94300075"

configure_logging(LOG_FILE)
driver = setup_driver()
try:
    #send_sms_twilio(PRODUCT_URL)
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

