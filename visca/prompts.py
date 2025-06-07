PAGE_CONTEXT_EXTRACTION_SYSTEM_PROMPT = """
Given the provided information about a webpage, your task is to provide a brief and abstract description of the webpage's primary purpose or function.
Output Guidelines:
* Brevity: Keep the description concise (aim for 1-2 sentences).
* Abstraction: Avoid specific details or variable names. Use general terms to describe the content and function. (Example: Instead of "a page showing results for searching for a TV," say "a page displaying search results for a product query.")
* Focus on Purpose: Prioritize describing the main intent of the page. What is it designed for the user to do or learn?
* No Extra Explanations: Just provide the context. Avoid adding commentary or assumptions.
""".strip()


"""
Based on analyzing several libraries, we identified a list of **Common Components**:
Typography, Image, Video, Icon, Navbar, Sidebar, Menu, Dropdown, Tabs, Breadcrumbs, Pagination, Button, Link, Form, Input, TextArea, Select, Checkbox, Radio, Switch, Slider, Label, TimePicker, DatePicker, Transfer, TreeSelect, AutoComplete, Upload, Card, List, Tree, Table, Avatar, Badge, Progress, Alert, Toast, Tooltip, Carousel, Accordion, Skeleton, Chip, Spinner, Timeline, Modal, Dialog, Popover, Chart, Map, Calendar

Considering the category definition and the common components, use the following rules for classification:
1. **Homogeneity is Key for Lists**: A segment qualifies as a List only if it consists *solely* of repetitions of the same type of child segment (Component).
2. **Additional Items Rule**: If a segment contains a repetition of homogeneous items (suggesting a List) BUT also includes *any* other distinct element(s) (like headers, footers, pagination controls, sidebars, titles *outside* the repeated items), it MUST be classified as a **Container**. Do NOT classify it as a List in this case.
3. **Hierarchy**: Containers can contain anything. Lists contain multiple instances of one Component type. Components represent single semantic units but can internally be complex.
4. **Common Components**: If a segment's screenshot *explicitly* matches one of the defined common components, it should be classified as a Component.

* **Compare against common components**: Determine if the segment matches any of the provided common components to see if the segment can be potentially a component.
"""


CLASSIFICATION_AND_CONTEXT_PROMPT = """
You are an expert UI developer tasked with the following tasks:
1. Classifying a provided webpage segment screenshot into one of the following three categories: Containers, Lists, or Components.
2. Predicting a contextual description and a title for the given segment.

You will be provided with the following inputs:
* Page Context: The overall page description generated previously, providing broad situational awareness.
* Screenshot: The segment's screenshot serving as the primary source for its content and layout.
* Ancestor Context: The contextual description(s) previously generated for the current segment's ancestors.

# Classification Task
For classification, we have defined the following categories:
* **Containers**: Structures primarily responsible for organizing diverse content. They do not inherently possess the semantic meaning of the elements they contain. They can hold any type of segment (Containers, Lists, or Components). Example: A whole page layout, a sidebar containing various widgets.
* **Lists**: Segments characterized by the repetition of multiple (more than one) homogeneous child segments (which are typically Components). These repetitions aggregate related information, often with some structural redundancy between items. Example: A product search results grid or a list of articles.
* **Components**: Fundamental, coherent semantic units of information. They represent a distinct piece of content or functionality. A Component might contain sub-components or even lists within it. Example: A single product card within a search results list, a user profile widget, a navigation bar.

Use the following rules for classification:
1. **Homogeneity is Key for Lists**: A segment qualifies as a List only if it consists *solely* of repetitions of the same type of child segment (Component).
2. **Additional Items Rule**: If a segment contains a repetition of homogeneous items (suggesting a List) BUT also includes *any* other distinct element(s) (like headers, footers, pagination controls, sidebars, titles *outside* the repeated items), it MUST be classified as a **Container**. Do NOT classify it as a List in this case.
3. **Hierarchy**: Containers can contain anything. Lists contain multiple instances of one Component type. Components represent single semantic units but can internally be complex.

# Context Extraction Task
Given the provided information about a segment on an HTML page, you should provide a brief and abstract description of the segment's purposes or functions.
Context Output Guidelines:
* Brevity: Keep the description concise (aim for 1-2 sentences).
* Abstraction: Avoid specific details or variable names. Use general terms to describe the content and function.
* Focus on Purpose: Prioritize describing the main intentions of the segment. What is it designed for the user to do or learn?

Furthermore, based on the predicted segment context, predict a concise, descriptive title in PascalCase (e.g., `ProductGrid`, `ArticleTeaser`, `UserProfileHeader`, `MainPageLayout`, `NavigationBar`, `FooterLinks`).

# Output Requirements
You MUST generate a step-by-step Chain-of-Thought reasoning process before providing the final classification, context, and title. Follow these steps in your reasoning:

* **Analyze the screenshot**: Briefly describe the visual elements and structure present in the image. Don't miss ANY SECTIONS in the screenshot. The segment includes the whole screenshot.
* **Identify the main structure/purpose**: Determine if the segment primarily serves to organize diverse content (potential Container), repeat similar items (potential List), or represent a single semantic unit (Component).
* **Check for homogeneity (if applicable)**: If the structure involves repetition, assess if the repeated child segments are homogeneous (same type and structure).
* **Check for additional items (if applicable)**: Look for any elements within the segment that are *not* part of the identified repetition (if any). This is crucial for distinguishing Lists from Containers.
* **Apply the classification rules**: Based on the analysis, explicitly state how the definitions and critical rules lead to the classification. Pay close attention to the "Additional Items Rule" if repetition is present.
* **Determine Segment Context**: Based on the content and structure identified, propose a concise, descriptive contextual description for the segment.
* **Determine Segment Title**: Based on the context identified, propose a concise, descriptive title for the segment in PascalCase (e.g., `ProductGrid`, `ArticleTeaser`, `UserProfileHeader`, `MainPageLayout`).
* **Conclusion**: State the final determined class and the predicted context and title based on the rule application and context determination.

Finally, format your entire output as follows:
* Enclose your step-by-step reasoning within `<Reasoning>` tags.
* Enclose the final classification, context, and title within `<Response>` tags using the following structure: `<Response><Classification>CategoryName</Classification><Context>PredictedContext</Context><Title>PredictedTitle</Title></Response>`.
* The predicted class should be one of 'Container', 'List', or 'Component'.
* Do NOT include ANY text outside of these three tags.
""".strip()


COMPONENT_GENERATION_PROMPT = """
You are an expert React developer. Your task is to generate precise React JSX based on an image screenshot of a webpage segment and a provided classification of that segment. You MUST use a predefined list of allowed components and ensure NO PLACEHOLDERS are used for any visible content.

# Input Provided by User:
1.  **Segment Classification:** This will be either `SegmentIsListOfItems` or `SegmentIsSingularComponent`.
2.  **Element's Screenshot:** The image of the webpage segment.
3.  **(Optional) Element's HTML Code:** For precise text/attribute extraction.
4.  **(Optional) Hierarchical Context:** For understanding role and placement.

# Available Components:
Typography, Image, Video, Icon, Navbar, Sidebar, Menu, Dropdown, Tabs, Breadcrumbs, Pagination, Button, Link, Form, Input, TextArea, Select, Checkbox, Radio, Switch, Slider, Label, TimePicker, DatePicker, Transfer, TreeSelect, AutoComplete, Upload, Card, List, Tree, Table, Avatar, Badge, Progress, Alert, Toast, Tooltip, Carousel, Accordion, Skeleton, Chip, Spinner, Timeline, Modal, Dialog, Popover, Chart, Map, Calendar

# --- Core Analysis & JSX Generation Process ---

**Internal Reasoning Step 1: Content Extraction & Initial Setup**
* Examine the provided image of the entire segment.
* **Explicitly extract and note ALL visible textual content VERBATIM** from the entire segment.
* **Describe all images:** For each image in the segment, provide a concise description.
* Note the user-provided `Segment Classification`.

---
## **PATH A: If User Provided Classification is `SegmentIsListOfItems`**
---

**Internal Reasoning Step 2.A: List Item Analysis & Type Determination (Redundant vs. Static)**
* Focus on the individual items within the list.
* **Definition - `RedundantList`:** Items appear as interchangeable examples from a potentially larger dataset. They share the exact same structure but display different data content. Implies dynamic rendering. (Goal: JSX for ONE representative item).
* **Definition - `StaticList`:** Items represent a fixed, finite set of unique options or links. Each item often has a distinct purpose/text. Implies static rendering. (Goal: JSX for ALL items).
* Based on visual characteristics and extracted content of the list items, conclude if the list is a `RedundantList` or a `StaticList`.

**JSX Generation Guidelines (If `SegmentIsListOfItems`):**

* **General List Item Guidelines (CRITICAL - APPLY TO BOTH LIST TYPES):**
    * **USE ACTUAL CONTENT - NO PLACEHOLDERS:** All text (labels, button text, prices, etc.) MUST be the verbatim text from the image. Image `alt` text must be descriptive. Link text must be verbatim. Input placeholders must be verbatim.
    * Use Provided Components ONLY.
    * Utilize subcomponents (e.g., `Card.Body`, `List.Item`) where appropriate.
    * No React Fragments for the outputted item(s).

* **IF `RedundantList`:**
    * **Generate JSX for a SINGLE Representative Item:** Use actual content from *one typical instance*.
    * **Name Attribute:** Include a `name` attribute on the top-level component of this single item (e.g., `name="ProductListItem"`).
    * **Output:** Only the JSX for this single representative item.

* **IF `StaticList`:**
    * **Generate JSX for the ENTIRE List:** Explicitly render *all visible, unique items* with their specific actual content.
    * **Name Attribute:** Include a `name` attribute on the top-level component representing the entire list container (e.g., `name="MainMenuNav"`).
    * **Keys:** Include a unique `key` prop on each direct list item.
    * **Output:** Only the static JSX for the entire list with all items explicitly rendered.

---
## **PATH B: If User Provided Classification is `SegmentIsSingularComponent`**
---

**Internal Reasoning Step 2.B: Component Sub-Structure Analysis**
* The segment is a single, cohesive component. Analyze its internal structure.
* Identify and classify its main parts:
    * **`StaticSubStructure`**: Parts of the component that are fixed or unique (e.g., a card's main title, a form's overall structure, a table's header section `Table.Header`, a modal's title bar).
    * **`InternalRedundantCollection`**: A collection of repeating, structurally similar items *within* the singular component. This is common for:
        * **Table Rows:** (e.g., items within `Table.Body`).
        * **List Items within a larger component:** (e.g., features listed in a `Card`, items in an embedded `List`).
        * **Carousel Slides:** (items within a `Carousel`).
        * **Accordion Panels:** (items within an `Accordion`).
        * **Tab Panels that contain lists of similar items.**
        The goal for these is to render the static container/parts and **one representative item** from the collection.
    * **`SingularSubElement`**: Distinct, non-repeating elements that aren't part of a collection (e.g., a standalone button, a descriptive paragraph not in a list).
* For example, in a Table component:
    * The `Table.Header` (or equivalent structure for column titles) is a `StaticSubStructure`.
    * The collection of `Table.Row` elements (or equivalent) within the table body is an `InternalRedundantCollection`.

**JSX Generation Guidelines (If `SegmentIsSingularComponent`):**

* **General Singular Component Guidelines (CRITICAL):**
    * **USE ACTUAL CONTENT - NO PLACEHOLDERS:** All text MUST be verbatim. Image `alt` text descriptive. Link text verbatim. Input placeholders verbatim.
    * Use Provided Components ONLY.
    * Structure logically; use subcomponents (e.g., `Modal.Body`, `Table.Cell`).
    * No React Fragments for the final output.

* **JSX for the ENTIRE Singular Component:**
    * The generated JSX must represent the *complete component's structure*.
    * **Rendering `StaticSubStructure` and `SingularSubElement` parts:** Render these fully and explicitly with their actual content as seen in the screenshot.
    * **Rendering `InternalRedundantCollection` parts (SPECIAL HANDLING):**
        * Render any static container elements for the collection (e.g., `Table.Header`, the main `Carousel` frame, the `Accordion` structure).
        * Then, from the collection of repeating items (e.g., table rows, slides, panels), generate JSX for **ONLY ONE representative item**. Use actual content from *one typical instance* visible in the screenshot.
        * Example for a Table: Render the `Table.Header` with all its actual column titles. Then, render *one* `Table.Row` with actual cell content from a single row in the image.
    * **Name Attribute:** Include a `name` attribute on the top-level of the generated component (e.g., `name="OwnerDetailsTable"`, `name="ProductDisplayCard"`).
    * **Output:** The JSX for this entire singular component, with internal redundant collections represented by a single item.

# Output Format:
You MUST provide your response in the following exact XML structure:

```xml
<Reasoning>
1.  **Content Extraction & Initial Setup:**
    * User-Provided Classification: [`SegmentIsListOfItems` OR `SegmentIsSingularComponent`]
    * Extracted Text: [List all verbatim text]
    * Image Descriptions: [List descriptions for all images]

2.  **Detailed Analysis (Path-Dependent):**
    * **(If `SegmentIsListOfItems`):**
        * List Item Analysis: [Describe items, assess similarities/differences in content and structure]
        * Conclusion: [`RedundantList` OR `StaticList`]
    * **(If `SegmentIsSingularComponent`):**
        * Component Sub-Structure Analysis:
            * Static Sub-structures: [Identify and describe, e.g., "Table header with columns: Name, Address..."]
            * Internal Redundant Collections: [Identify and describe, e.g., "Table rows, each with Name, Address..."]
            * Singular Sub-Elements: [Identify and describe, if any]

3.  **Final Generation Strategy:** [Briefly state what will be generated based on the analysis. Examples:
    * "Generate JSX for a single representative item from the top-level RedundantList."
    * "Generate JSX for all items in the top-level StaticList."
    * "Generate JSX for the entire SingularComponent (OwnerDetailsTable), including the static Table.Header and one representative Table.Row for the InternalRedundantCollection of rows."]
</Reasoning>
<JsxOutput>
[The generated React JSX code (WITH CORRECT INDENTATION), adhering strictly to the determined path, classification, and ALL guidelines, especially "USE ACTUAL CONTENT - NO PLACEHOLDERS" and rules for representing redundant parts.]
</JsxOutput>

# Output Requirements:
* Refrain from generating the representation for any components that is not visible in the screenshot.
* Refrain from leaving any comments in the generated code.
""".strip()



# COMPONENT_GENERATION_PROMPT = """
# Generate a React component based on an image and/or a list of its subcomponent children.

# Select from the following components:
# - Typography
# - Image
# - Video
# - Icon
# - Navbar
# - Sidebar
# - Menu
# - Dropdown
# - Tabs
# - Breadcrumbs
# - Pagination
# - Button
# - Link
# - Form
# - Input
# - TextArea
# - Select
# - Checkbox
# - Radio
# - Switch
# - Slider
# - Label
# - TimePicker
# - DatePicker
# - Transfer
# - TreeSelect
# - AutoComplete
# - Upload
# - Card
# - List
# - Tree
# - Table
# - Avatar
# - Badge
# - Progress
# - Alert
# - Toast
# - Tooltip
# - Carousel
# - Accordion
# - Skeleton
# - Chip
# - Spinner
# - Timeline
# - Modal
# - Dialog
# - Popover
# - Chart
# - Map
# - Calendar

# Guidelines:
# - Automatically structure components, excluding structural tags.
# - Include only a "name" attribute that conveys the component's purpose, e.g., `name="ProductCard"`.
# - Include appropriate subcomponents for elements like Modals, e.g., `Modal.Body`, `Modal.Title`.
# - Return only the JSX for the render function, without hypothetical templates.
# - Avoid using React fragments.
# - If given children for a component, use the children to generate the parent component, don't write everything from scratch.

# # Input
# * Element's Screenshot: The screenshot provides the primary evidence of the component's appearance, layout, and visible sub-elements.
# * Element's HTML Code: The corresponding HTML source is included to allow extracting precise textual content, specific attributes (e.g., href URLs, src image paths), or structural nuances potentially missed by visual analysis alone.
# * Hierarchical Context: The page-level context description and the natural language descriptions generated for the element's ancestors are provided. This informs about the component's placement and likely role within the broader application structure, aiding disambiguation.

# # Output Format

# Return a JSX representation of the components within the render function.
# """.strip()


# LIST_COMPONENT_GENERATION_PROMPT = """
# You are tasked with generating React JSX based on an image screenshot of a webpage segment that has been previously classified as a **List**.

# **Your first critical step is to analyze the provided image, paying close attention to the actual content (text, images), and determine if this list functions as a `RedundantList` or a `StaticList` based on its visual characteristics.** Then, generate the appropriate React JSX according to the type you determine, following the specific guidelines for that type, ensuring **NO PLACEHOLDERS** are used for visible content.

# * **Definition - Redundant List:** Items appear as interchangeable examples drawn from a potentially larger dataset (e.g., product search results, article feeds, image gallery items). Items usually share the exact same structure but display different data content (text, images). Implies dynamic rendering from data.
# * **Definition - Static List:** Items represent a fixed, finite set of unique options or links (e.g., main navigation menu items, settings options, tabs). Each item often has a distinct purpose, text, and potentially icon or link, even if structurally similar. Implies static rendering of a predefined set.

# Use components from the following list for your generation:

# # Available Components:
# - Typography
# - Image
# - Video
# - Icon
# - Navbar
# - Sidebar
# - Menu
# - Dropdown
# - Tabs
# - Breadcrumbs
# - Pagination
# - Button
# - Link
# - Form
# - Input
# - TextArea
# - Select
# - Checkbox
# - Radio
# - Switch
# - Slider
# - Label
# - TimePicker
# - DatePicker
# - Transfer
# - TreeSelect
# - AutoComplete
# - Upload
# - Card
# - List
# - Tree
# - Table
# - Avatar
# - Badge
# - Progress
# - Alert
# - Toast
# - Tooltip
# - Carousel
# - Accordion
# - Skeleton
# - Chip
# - Spinner
# - Timeline
# - Modal
# - Dialog
# - Popover
# - Chart
# - Map
# - Calendar

# # Step 1: Internal Reasoning & Decision (Chain-of-Thought)
# Before generating JSX, perform and document the following reasoning steps:
# 1.  **Analyze List Items & Extract Content:** Describe the visual characteristics of items. **Explicitly extract and note the *actual text labels, button text, prices, visible link text, input placeholders*, etc.** Describe the content of images. Note similarities/differences in structure *and* the extracted/described content.
# 2.  **Assess Redundancy vs. Uniqueness & Function:** Based on the visual analysis and *extracted content*, assess the nature of the items. Do they primarily function as examples of data (different content, same structure -> Redundancy)? Or do they form a specific, fixed set of distinct options/navigations (often unique text/icons/links -> Static)?
# 3.  **Conclude List Type:** Explicitly state whether you classify this list as `Redundant` or `Static` for the purpose of JSX generation based on your assessment.

# # Step 2: JSX Generation Guidelines (Apply based on your Step 1 Conclusion)

# **General Guidelines (Apply in both cases - HIGHEST PRIORITY):**
# * **USE ACTUAL CONTENT - NO PLACEHOLDERS (CRITICAL):**
#     * For any text elements (`Typography`, `Button`, `Link` text, `Labels`, `Menu.Item` text, etc.), you **MUST** use the **exact verbatim text** visible in the image segment.
#     * **DO NOT** use generic placeholders like "Product Name", "Description here", "...", "Click Me", "$XX.XX", "Menu Item", or any similar template text.
#     * For images (`Image`): Provide a **descriptive `alt` attribute** based on what the image actually depicts (e.g., `alt="Red sports car parked on a street"`). If the image is purely decorative and conveys no meaning, use `alt=""`. **DO NOT** use placeholder alt text like "Image" or "Product Image". For the `src`, if the URL isn't knowable, use a standard non-descript path like `src="/placeholder-image.png"`.
#     * For links (`Link`, `Menu.Item` linking): Use the **actual visible text** for the link content. For the `href` attribute, if the destination is clear from the context or text (e.g., text is "About Us", use `href="/about-us"`), infer it. If the link destination is unclear but it's clearly interactive, use `href="#"`.
#     * For form inputs (`Input`, `TextArea`): If there is visible placeholder text *in the image*, use that **exact text** for the `placeholder` attribute in the JSX.
# * **Use Provided Components:** Select the most appropriate component(s) from the "Available Components" list. Structure components automatically; avoid unnecessary generic `<div>` or `<span>` unless part of a chosen component's intended structure.
# * **Subcomponents:** Use appropriate nested components where the chosen component provides them (e.g., `Card.Body`, `Menu.Item`, `List.Item`).
# * **No Fragments:** The final JSX output must have a single root element.
# * **Use Children (If Provided):** If the input includes pre-generated JSX for children components, structure the parent component logically around them.
# * **Keys (for Static List Items):** If generating items for a `Static` list, include a sensible `key` prop on each item (e.g., `Menu.Item`, `List.Item`) based on its unique extracted text or inferred purpose.

# **IF you concluded the list is `Redundant`:**
# * **Generate JSX for a SINGLE Representative Item:** Focus on accurately representing the visual structure and **using the actual visible content** (text, image descriptions, prices etc. extracted from *one typical instance*) of *one example item* from the list. Adhere strictly to the "USE ACTUAL CONTENT - NO PLACEHOLDERS" guideline.
# * **Name Attribute (Single Item):** Include **only** a `name` attribute on the *top-level* component of the generated *single item*. Name it based on the item's role (e.g., `name="ProductCard"`, `name="ArticleTeaser"`).
# * **JSX Only (Single Item):** Output *only* the JSX for *one item*. No imports, function definitions, returns, loops (`.map`).

# **IF you concluded the list is `Static`:**
# * **Generate JSX for the ENTIRE List:** Represent the *complete list structure* including *all visible, unique items* explicitly rendered, **using the actual content extracted from the image for each specific item**. Adhere strictly to the "USE ACTUAL CONTENT - NO PLACEHOLDERS" guideline.
# * **Name Attribute (List Container):** Include **only** a `name` attribute on the **top-level** component representing the *entire list container*. Name it based on the list's overall purpose (e.g., `name="MainMenuNav"`, `name="SettingsOptionsList"`).
# * **JSX Only (Entire List - Static & Explicit):** Output *only* the static JSX for the *entire list* with all items rendered explicitly. No imports, function definitions, returns, loops (`.map`).

# # Input
# * Element's Screenshot: The screenshot provides the primary evidence of the component's appearance, layout, and visible sub-elements.
# * Element's HTML Code: The corresponding HTML source is included to allow extracting precise textual content, specific attributes (e.g., href URLs, src image paths), or structural nuances potentially missed by visual analysis alone.
# * Hierarchical Context: The page-level context description and the natural language descriptions generated for the element's ancestors are provided. This informs about the component's placement and likely role within the broader application structure, aiding disambiguation.

# # Output Format:
# You MUST provide your response in the following exact structure, with no additional text outside the specified tags:

# ```xml
# <Reasoning>
# 1.  **Analyze List Items & Extract Content:** [Your detailed analysis including *extracted text* and *image descriptions*]
# 2.  **Assess Redundancy vs. Uniqueness & Function:** [Your assessment based on analysis and extracted content]
# 3.  **Conclude List Type:** [The final conclusion: Redundant or Static]
# </Reasoning>
# <JsxOutput>
# [The generated React JSX code - adhering strictly to the NO PLACEHOLDERS rule]
# </JsxOutput>
# """.strip()
