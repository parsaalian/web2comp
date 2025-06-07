import os
import io
import time
from typing import Tuple

from PIL import Image

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


def create_driver(headless=True) -> WebDriver:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--hide-scrollbars")  # Hide scrollbars to avoid affecting layout
    chrome_options.add_argument("--force-device-scale-factor=1")  # Force known scale factor
    chrome_options.add_argument("--disable-gpu")
    
    chrome_path = ChromeDriverManager().install()
    if "THIRD_PARTY_NOTICES.chromedriver" in chrome_path:
        chrome_path = chrome_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
    os.chmod(chrome_path, 755)
    
    driver = Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    return driver


def ensure_page_loaded(driver: WebDriver, timeout: int):
    try:
        # Wait for document ready state
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Wait a bit more for any JS-triggered rendering to complete
        time.sleep(2)
    except Exception as e:
        print(f"Warning: Page load wait timed out: {e}")


def get_driver_dpr(driver: WebDriver) -> float:
    return float(driver.execute_script("return window.devicePixelRatio") or 1)


def get_current_page_dimensions(driver: WebDriver) -> Tuple[int, int]:
    dimensions = driver.execute_script("""
        return {
            scrollWidth: document.documentElement.scrollWidth,
            scrollHeight: document.documentElement.scrollHeight
        }
    """)

    return (
        dimensions['scrollWidth'],
        # sometimes the exact size misses the footer
        dimensions['scrollHeight'] + 256
    )


def resize_screenshot(screenshot: Image.Image, width: int, height: int, device_pixel_ratio=1.0) -> Image.Image:
    """
    Check if we need to resize the screenshot to match the DOM dimensions.
    This is crucial for correct alignment.
    """
    resized_screenshot = screenshot
    screenshot_width, screenshot_height = screenshot.size
    
    if (screenshot_width != width or screenshot_height != height) and device_pixel_ratio != 1.0:
        print(f"Resizing screenshot from {screenshot.size} to match DOM dimensions {width}x{height}")
        resized_screenshot = screenshot.resize((width, height), Image.Resampling.LANCZOS)
    
    return resized_screenshot


def capture_full_page_screenshot(driver: WebDriver) -> Image.Image:
    total_width, total_height = get_current_page_dimensions(driver)
    device_pixel_ratio = get_driver_dpr(driver)
    
    # Set window size to capture full page
    driver.set_window_size(total_width, total_height)
    time.sleep(1)  # Wait for resize to complete
    
    # Take screenshot
    screenshot = driver.get_screenshot_as_png()
    screenshot_img = Image.open(io.BytesIO(screenshot))
    
    # Resize screenshot if required
    screenshot_img = resize_screenshot(
        screenshot=screenshot_img,
        width=total_width,
        height=total_height,
        device_pixel_ratio=device_pixel_ratio
    )
    
    return screenshot_img


def get_element_xpath(driver: WebDriver, element: WebElement) -> str:
    xpath_script = """
        function getPathTo(element) {
            if (element === document.body)
                return element.tagName;
            var ix= 0;
            var siblings= element.parentNode.childNodes;
            for (var i= 0; i<siblings.length; i++) {
                var sibling= siblings[i];
                if (sibling===element)
                    return getPathTo(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                if (sibling.nodeType===1 && sibling.tagName===element.tagName)
                    ix++;
            }
        }
        const path = getPathTo(arguments[0]);
        return '//' + path;
    """
    
    xpath = driver.execute_script(xpath_script, element)
    return xpath
