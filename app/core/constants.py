# app/core/constants.py

# Transaction Types
TX_RECEIVING       = "RECEIVING"
TX_ADJUSTMENT      = "ADJUSTMENT"
TX_WASTAGE         = "WASTAGE"
TX_INDENT_FULFILL  = "INDENT_FULFILL"
TX_SALE            = "SALE" # Future use

# Indent Statuses (Overall Indent)
STATUS_SUBMITTED   = "Submitted"
STATUS_PROCESSING  = "Processing"
STATUS_COMPLETED   = "Completed"
STATUS_CANCELLED   = "Cancelled"
ALL_INDENT_STATUSES = [
    STATUS_SUBMITTED, STATUS_PROCESSING,
    STATUS_COMPLETED, STATUS_CANCELLED
]

# Indent Item Statuses
ITEM_STATUS_PENDING_ISSUE = "Pending Issue"
ITEM_STATUS_FULLY_ISSUED = "Fully Issued"
ITEM_STATUS_PARTIALLY_ISSUED = "Partially Issued"
ITEM_STATUS_CANCELLED_ITEM = "Item Cancelled" # Specific to item line cancellation

ALL_INDENT_ITEM_STATUSES = [
    ITEM_STATUS_PENDING_ISSUE, ITEM_STATUS_FULLY_ISSUED,
    ITEM_STATUS_PARTIALLY_ISSUED, ITEM_STATUS_CANCELLED_ITEM # Updated constant name
]

# Purchase Order Statuses
PO_STATUS_DRAFT = "Draft"
PO_STATUS_ORDERED = "Ordered"
PO_STATUS_PARTIALLY_RECEIVED = "Partially Received"
PO_STATUS_FULLY_RECEIVED = "Fully Received"
PO_STATUS_CANCELLED = "Cancelled" # Same constant as Indent, but contextually for POs

ALL_PO_STATUSES = [
    PO_STATUS_DRAFT, PO_STATUS_ORDERED, PO_STATUS_PARTIALLY_RECEIVED,
    PO_STATUS_FULLY_RECEIVED, PO_STATUS_CANCELLED
]

# GRN Related (not strictly statuses, but for reference if needed later)
# No GRN-specific statuses defined yet, as GRNs are typically just records of receipt.