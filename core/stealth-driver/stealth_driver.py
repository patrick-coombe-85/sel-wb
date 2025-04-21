import undetected_chromedriver as uc
import time
import os
import random
import zipfile
import atexit
import logging
from datetime import datetime
import proxy_config

# Generate timestamp for filenames
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Setup logging with timestamped filename
log_filename = f"stealth_driver_{timestamp}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

def create_proxy_extension(proxy, username, password):
    """Creates a Chrome extension to handle proxy authentication."""
    manifest_json = """{
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy",
        "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }"""

    background_js = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "https",
                host: "{proxy.split(':')[1][2:]}",
                port: parseInt("{proxy.split(':')[2]}")
            }},
            bypassList: ["localhost"]
        }}
    }};
    
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{username}",
                    password: "{password}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    plugin_file = f"proxy_auth_plugin_{timestamp}.zip"
    with zipfile.ZipFile(plugin_file, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_file

def get_next_proxy():
    if not os.path.exists(proxy_config.LAST_PROXY_FILE):
        last_index = -1
    else:
        with open(proxy_config.LAST_PROXY_FILE, "r") as file:
            try:
                last_index = int(file.read().strip())
            except ValueError:
                last_index = -1

    next_index = (last_index + 1) % len(proxy_config.PROXIES)
    next_proxy = proxy_config.PROXIES[next_index]["https"]

    with open(proxy_config.LAST_PROXY_FILE, "w") as file:
        file.write(str(next_index))

    logging.info(f"Switching to proxy #{next_index + 1}: {next_proxy}")
    return next_proxy

def human_pause(min_sec=0.5, max_sec=1.5):
    time.sleep(random.uniform(min_sec, max_sec))

def create_stealth_driver(proxy):
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--start-maximized")
    options.add_argument("--mute-audio")

    user_agent = proxy_config.get_random_user_agent()
    options.add_argument(f"user-agent={user_agent}")
    logging.info(f"Using User-Agent: {user_agent}")

    username = proxy_config.USERNAME
    password = proxy_config.PASSWORD
    plugin_file = create_proxy_extension(proxy, username, password)

    @atexit.register
    def cleanup():
        if os.path.exists(plugin_file):
            os.remove(plugin_file)
            logging.info(f"Deleted temporary proxy extension: {plugin_file}")

    options.add_argument(f"--load-extension={plugin_file}")
    driver = uc.Chrome(options=options, version_main=proxy_config.CHROME_VERSION)

    stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth });
        Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight });
        window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };

        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );

        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter(parameter);
        };

        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {
            const ctx = this.getContext('2d');
            ctx.fillStyle = 'rgb(100,100,100)';
            ctx.fillRect(10, 10, 100, 100);
            return toDataURL.apply(this, arguments);
        };

        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
        Object.defineProperty(navigator, 'connection', {
            get: () => ({ downlink: 10, effectiveType: '4g', rtt: 50 })
        });
    """

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": stealth_js
    })

    logging.info("Stealth driver initialized successfully.")
    return driver

def human_type(element, text, min_delay=0.05, max_delay=0.2):
    """Simulates human typing."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))
