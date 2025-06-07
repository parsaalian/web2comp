import os
import json
import traceback
from pathlib import Path
from typing import List, TypedDict

import numpy as np
from PIL import Image

from selenium.webdriver.remote.webdriver import WebDriver

from visca.browser import (
    get_driver_dpr,
    capture_full_page_screenshot,
)
from visca.html_processing import clean_html


class ElementInfo(TypedDict):
    tag: str
    id: str
    classes: List[str]
    x: int
    y: int
    width: int
    height: int
    visible: bool
    text: str
    html: str
    xpath: str
    screenshot: str
    index: int
    gt_dataBlock: str     
    gt_dataBlockType: str


class TextElementInfo(ElementInfo):
    isInteractive: bool


def extract_dom_elements(driver: WebDriver) -> List[ElementInfo]:
    """
    Extract DOM elements with accurate bounding boxes and XPath information.
    """
    script = """
    function getElementInfo(element, index) {
        // Get element position relative to the page (not viewport)
        const rect = element.getBoundingClientRect();
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Calculate absolute positions (relative to document, not viewport)
        const absoluteLeft = rect.left + scrollLeft;
        const absoluteTop = rect.top + scrollTop;

        // NEW - Generate XPath for element
        function getXPath(element) {
            if (!element || element.nodeType !== Node.ELEMENT_NODE) {
                return '';
            }
            const segments = [];
            // Walk up the tree, collecting tagName[index] for each element
            while (element && element.nodeType === Node.ELEMENT_NODE) {
                let idx = 1;
                let sib = element.previousSibling;
                // Count how many preceding siblings share the same tag name
                while (sib) {
                if (sib.nodeType === Node.ELEMENT_NODE && sib.tagName === element.tagName) {
                    idx++;
                }
                sib = sib.previousSibling;
                }
                segments.unshift(`${element.tagName.toLowerCase()}[${idx}]`);
                element = element.parentNode;
            }
            // Prepend '//' so the path starts with "//html[1]/body[1]/…"
            return '//' + segments.join('/');
        }
        
        function getElementIdx(element) {
            let count = 1;
            let sib = element.previousSibling;
            
            while (sib) {
                if (sib.nodeType === Node.ELEMENT_NODE && sib.tagName === element.tagName) {
                    count++;
                }
                sib = sib.previousSibling;
            }
            
            return count;
        }
        
        return {
            tag: element.tagName.toLowerCase(),
            id: element.id,
            classes: Array.from(element.classList),
            gt_dataBlock:      element.getAttribute('data-block')       || null,
            gt_dataBlockType:  element.getAttribute('data-block-type')  || null,
            x: Math.round(absoluteLeft),
            y: Math.round(absoluteTop),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            visible: rect.width > 5 && rect.height > 5 && 
                        getComputedStyle(element).display !== 'none' && 
                        getComputedStyle(element).visibility !== 'hidden',
            text: element.textContent.trim().substring(0, 50),
            html: element.outerHTML,
            xpath: getXPath(element),
            index: index
        };
    }
    
    function isElementVisible(element) {
        if (!element) return false;
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && 
                style.visibility !== 'hidden' && 
                style.opacity !== '0' &&
                element.offsetWidth > 0 &&
                element.offsetHeight > 0;
    }
    
    function buildElementHierarchy() {
        const elements = [];
        
        function processElement(element, parentIndex = null) {
            if (!element || element.nodeType !== 1) return;
            
            // Skip invisible elements
            if (!isElementVisible(element)) return;
            
            const index = elements.length;
            const info = getElementInfo(element, index);
            
            // Skip elements outside the viewport or too small
            if (info.width < 5 || info.height < 5 || 
                info.x < 0 || info.y < 0) return;
            
            elements.push(info);
            
            // Process children
            for (let i = 0; i < element.children.length; i++) {
                processElement(element.children[i], index);
            }
        }
        
        // Start with body
        processElement(document.body);
        
        return elements;
    }
    
    return buildElementHierarchy();
    """
    return driver.execute_script(script)


def extract_text_elements(driver: WebDriver) -> List[TextElementInfo]:
    """
    Detect text elements that might be important interactive components.
    """
    script = """
    function getTextElements() {
        const textElements = [];
        const smallElements = [];
        
        // CSS selectors for common small interactive elements
        const selectors = [
            'button', 'a', '.btn', '[role="button"]', 
            'input[type="submit"]', 'input[type="button"]',
            'label', '.label', '.tag', '.badge',
            'li a', '.menu-item', '.nav-item',
            '.icon', 'i.fa', 'i.material-icons',
            'img[alt]', '[aria-label]'
        ];
        
        // Find elements by selectors
        const elements = document.querySelectorAll(selectors.join(','));
        
        elements.forEach((element, index) => {
            const rect = element.getBoundingClientRect();
            const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            // Calculate absolute positions
            const absoluteLeft = rect.left + scrollLeft;
            const absoluteTop = rect.top + scrollTop;
            
            if (rect.width < 200 && rect.height < 100 && 
                rect.width > 10 && rect.height > 10 &&
                getComputedStyle(element).display !== 'none' && 
                getComputedStyle(element).visibility !== 'hidden') {

                // NEW - Generate XPath for element
                function getXPath(element) {
                    if (!element || element.nodeType !== Node.ELEMENT_NODE) {
                        return '';
                    }
                    const segments = [];
                    // Walk up the tree, collecting tagName[index] for each element
                    while (element && element.nodeType === Node.ELEMENT_NODE) {
                        let idx = 1;
                        let sib = element.previousSibling;
                        // Count how many preceding siblings share the same tag name
                        while (sib) {
                        if (sib.nodeType === Node.ELEMENT_NODE && sib.tagName === element.tagName) {
                            idx++;
                        }
                        sib = sib.previousSibling;
                        }
                        segments.unshift(`${element.tagName.toLowerCase()}[${idx}]`);
                        element = element.parentNode;
                    }
                    // Prepend '//' so the path starts with "//html[1]/body[1]/…"
                    return '//' + segments.join('/');
                }
                
                function get_XPath(element) {
                    if (!element || typeof element !== 'object' || element.nodeType !== Node.ELEMENT_NODE) {
                        return ''; // Or throw an error for invalid input
                    }

                    if (element === document.body) {
                        return '/html/body';
                    }

                    let ix = 0;
                    const siblings = element.parentNode ? element.parentNode.childNodes : [];
                    for (let i = 0; i < siblings.length; i++) {
                            const sibling = siblings[i];
                        if (sibling === element) {
                            return `${getXPath(element.parentNode)}/${element.tagName.toLowerCase()}[${ix + 1}]`;
                        }
                            if (sibling && sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === element.tagName) {
                            ix++;
                        }
                    }

                    return ''; // Should not ideally reach here for valid elements within the document
                }
                
                smallElements.push({
                    tag: element.tagName.toLowerCase(),
                    id: element.id,
                    classes: Array.from(element.classList),
                    gt_dataBlock:     element.getAttribute('data-block')      || null,
                    gt_dataBlockType: element.getAttribute('data-block-type') || null,
                    x: Math.round(absoluteLeft),
                    y: Math.round(absoluteTop),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    visible: true,
                    text: element.textContent.trim().substring(0, 50),
                    html: element.outerHTML,
                    xpath: getXPath(element),
                    index: index,
                    isInteractive: element.tagName.toLowerCase() === 'a' || 
                                element.tagName.toLowerCase() === 'button' ||
                                element.hasAttribute('role')
                });
            }
        });
        
        return smallElements;
    }
    
    return getTextElements();
    """
    return driver.execute_script(script)


def scale_coordinates(dom_elements: List[ElementInfo], dpr: float = 1.0) -> List[ElementInfo]:
    """
    Scale coordinates if needed based on device pixel ratio.
    """
    # Only scale if device pixel ratio is different from 1
    if abs(dpr - 1.0) < 0.01:
        return dom_elements
        
    for e in dom_elements:
        # Scale coordinates and dimensions
        e['x'] = int(e['x'] / dpr)
        e['y'] = int(e['y'] / dpr)
        e['width'] = int(e['width'] / dpr)
        e['height'] = int(e['height'] / dpr)
        
    return dom_elements


def extract_elements_from_driver(driver: WebDriver):
    try:
        print(f"Processing {driver.current_url}...")
        
        dom_elements = extract_dom_elements(driver)

        small_elements = extract_text_elements(driver)
        
        # Merge small elements with main DOM elements
        for small_elem in small_elements:
            # Check if this element is already in dom_elements to avoid duplicates
            is_duplicate = False
            for dom_elem in dom_elements:
                if (dom_elem.get('xpath') == small_elem.get('xpath') or
                    (dom_elem.get('x') == small_elem.get('x') and
                    dom_elem.get('y') == small_elem.get('y') and
                    dom_elem.get('width') == small_elem.get('width') and
                    dom_elem.get('height') == small_elem.get('height'))):
                    is_duplicate = True
                    # Enhance existing element with interactive flag
                    if small_elem.get('isInteractive'):
                        dom_elem['isInteractive'] = True
                    break
            
            if not is_duplicate:
                dom_elements.append(small_elem)
        
        dom_elements = scale_coordinates(
            dom_elements,
            dpr=get_driver_dpr(driver)
        )
        
        # Filter super small elements
        dom_elements = list(filter(
            lambda e: e['width'] >= 10 and e['height'] >= 10,
            dom_elements
        ))
        
        return dom_elements
    except Exception as e:
        print(f"Error segmenting webpage: {e}")
        traceback.print_exc()


############################### OUTPUT UTILS ###############################


def extract_element_image_from_image(image: Image.Image, element):
    # Get element coordinates
    x, y = element['x'], element['y']
    w, h = element['width'], element['height']
    
    # Ensure coordinates are within image bounds
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    if x + w > image.shape[1]:
        w = image.shape[1] - x
    if y + h > image.shape[0]:
        h = image.shape[0] - y
    
    # Skip if element is too small or out of bounds
    if w <= 5 or h <= 5 or x >= image.shape[1] or y >= image.shape[0]:
        return None
    
    # Extract the element from the image
    element_img = image[y:y+h, x:x+w]
    
    return element_img


def create_element_image_filename(element):
    element_xpath = element.get('xpath', '').replace('//', '').replace('/', '_')
    return f"{element_xpath}.png"


def capture_element_screenshots(image, elements: List[ElementInfo], output_dir: str):
    """
    Capture screenshots of each element.
    """
    # Create output directory structure
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Convert PIL image to numpy array for processing
    img_np = np.array(image)
    
    screenshot_path = output_path / 'elements'
    screenshot_path.mkdir(exist_ok=True)
    
    for element in elements:
        try:
            element_img = extract_element_image_from_image(img_np, element)  # <- Disabled for Evaluation Efficiency
            
            if element_img is None: # <- Disabled for Evaluation Efficiency
                continue
            
            filename = create_element_image_filename(element)
            
            # Save the element image
            element_path = screenshot_path / filename
            Image.fromarray(element_img).save(element_path) #<- Disabled for Evaluation Efficiency
            
            # Add screenshot path to element info
            element['screenshot'] = str(element_path) # str(element_path.relative_to(output_path))
        
        except Exception as e:
            print(f"Error saving element: {e}")
    
    print(f"Element screenshots saved to {output_path}")
    
    return elements


def elements_to_json(elements: List[ElementInfo]):
    result = []
    
    for element in elements:
        result.append({
            # 'id': element.get('id', ''),
            'tag': element['tag'],
            'x': element['x'],
            'y': element['y'],
            'width': element['width'],
            'height': element['height'],
            'visible': element['visible'],
            'text': element.get('text', ''),
            # TODO: update the HTML code to keep only the container for the children
            # instead of storing the whole HTML. This way we can reconstruct the HTML
            # By traversing the children, which would be more memory efficient.
            'html': clean_html(element['html']).prettify(), # [:8192],
            'xpath': element['xpath'],
            'index': element['index'],
            'screenshot': element.get('screenshot', ''),
            'gt_dataBlock': element['gt_dataBlock'],
            'gt_dataBlockType': element['gt_dataBlockType']
        })
    
    return result


def save_elements(
    driver: WebDriver,
    result_dir: str,
    dom_elements
):
    os.makedirs(result_dir, exist_ok=True)
    
    image = capture_full_page_screenshot(driver)
    


    dom_elements_with_screenshot = capture_element_screenshots(
        image, dom_elements, result_dir
    )
    
    elements_json = elements_to_json(dom_elements_with_screenshot)
    
    # print(elements_json)
    
    with open(f'{result_dir}/segments.json', 'w', encoding='utf-8') as f:
        json.dump(elements_json, f)
    
    return dom_elements_with_screenshot
