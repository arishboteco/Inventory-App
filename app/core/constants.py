# app/core/constants.py

# ─────────────────────────────────────────────────────────
# TRANSACTION TYPE CONSTANTS
# ─────────────────────────────────────────────────────────
TX_RECEIVING = "RECEIVING"
TX_ADJUSTMENT = "ADJUSTMENT"
TX_WASTAGE = "WASTAGE"
TX_INDENT_FULFILL = "INDENT_FULFILL"
TX_SALE = "SALE"  # Future use

# ─────────────────────────────────────────────────────────
# INDENT STATUS CONSTANTS (Overall Indent)
# ─────────────────────────────────────────────────────────
STATUS_SUBMITTED = "Submitted"
STATUS_PROCESSING = "Processing"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"  # Used for overall Indent cancellation
ALL_INDENT_STATUSES = [
    STATUS_SUBMITTED,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
]

# ─────────────────────────────────────────────────────────
# INDENT ITEM STATUS CONSTANTS
# ─────────────────────────────────────────────────────────
ITEM_STATUS_PENDING_ISSUE = "Pending Issue"
ITEM_STATUS_FULLY_ISSUED = "Fully Issued"
ITEM_STATUS_PARTIALLY_ISSUED = "Partially Issued"
ITEM_STATUS_CANCELLED_ITEM = (
    "Item Cancelled"  # Specific to item line cancellation within an indent
)
ALL_INDENT_ITEM_STATUSES = [
    ITEM_STATUS_PENDING_ISSUE,
    ITEM_STATUS_FULLY_ISSUED,
    ITEM_STATUS_PARTIALLY_ISSUED,
    ITEM_STATUS_CANCELLED_ITEM,
]

# ─────────────────────────────────────────────────────────
# PURCHASE ORDER (PO) STATUS CONSTANTS
# ─────────────────────────────────────────────────────────
PO_STATUS_DRAFT = "Draft"
PO_STATUS_ORDERED = "Ordered"
PO_STATUS_PARTIALLY_RECEIVED = "Partially Received"
PO_STATUS_FULLY_RECEIVED = "Fully Received"
PO_STATUS_CANCELLED_PO = "Cancelled"  # Explicitly for PO, to avoid confusion if STATUS_CANCELLED is used for Indents
ALL_PO_STATUSES = [
    PO_STATUS_DRAFT,
    PO_STATUS_ORDERED,
    PO_STATUS_PARTIALLY_RECEIVED,
    PO_STATUS_FULLY_RECEIVED,
    PO_STATUS_CANCELLED_PO,
]

# ─────────────────────────────────────────────────────────
# GOODS RECEIVED NOTE (GRN) RELATED CONSTANTS
# ─────────────────────────────────────────────────────────
# No GRN-specific statuses defined yet, as GRNs are typically records of receipt events.
# Their impact is on PO status and stock levels.

# ─────────────────────────────────────────────────────────
# UI PLACEHOLDER & FILTER CONSTANTS
# ─────────────────────────────────────────────────────────
# General Select Placeholders
PLACEHOLDER_SELECT_ITEM = "-- Select an Item --"
PLACEHOLDER_SELECT_SUPPLIER = "-- Select Supplier --"
PLACEHOLDER_SELECT_INDENT_PROCESS = "-- Select Indent (MRN) to Process --"
PLACEHOLDER_SELECT_MRN_PDF = "-- Select MRN for PDF --"  # Used in 5_Indents.py

# Filter Defaults
FILTER_ALL_TYPES = "-- All Types --"  # For transaction type filters
FILTER_ALL_STATUSES = "All Statuses"  # For status filters (e.g., POs, Indents)
FILTER_ALL_DEPARTMENTS = "All Departments"  # For department filters
FILTER_ALL_CATEGORIES = "All Categories"  # For category filters (e.g., in 1_Items.py)
FILTER_ALL_SUBCATEGORIES = (
    "All Sub-Categories"  # For sub-category filters (e.g., in 1_Items.py)
)

# Item Selection Specific Placeholders (primarily used in Indents page - 5_Indents.py)
PLACEHOLDER_SELECT_DEPARTMENT_FIRST = "-- Select Department First --"
PLACEHOLDER_NO_ITEMS_FOR_DEPARTMENT = "-- No items permitted for this department --"
PLACEHOLDER_NO_ITEMS_AVAILABLE = (
    "No items available"  # General placeholder if item master is empty
)
PLACEHOLDER_ERROR_LOADING_ITEMS = "Error loading items"  # If item fetching fails
