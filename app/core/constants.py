# app/core/constants.py

# Transaction Types
TX_RECEIVING       = "RECEIVING"
TX_ADJUSTMENT      = "ADJUSTMENT"
TX_WASTAGE         = "WASTAGE"
TX_INDENT_FULFILL  = "INDENT_FULFILL"
TX_SALE            = "SALE"

# Indent Statuses (Overall Indent)
STATUS_SUBMITTED   = "Submitted"
STATUS_PROCESSING  = "Processing"  # Indent is being worked on, items partially issued
STATUS_COMPLETED   = "Completed"   # All items actioned (issued, or remaining acknowledged)
STATUS_CANCELLED   = "Cancelled"   # Entire indent cancelled
ALL_INDENT_STATUSES = [
    STATUS_SUBMITTED, STATUS_PROCESSING,
    STATUS_COMPLETED, STATUS_CANCELLED
]

# Indent Item Statuses (NEW)
ITEM_STATUS_PENDING_ISSUE = "Pending Issue"
ITEM_STATUS_FULLY_ISSUED = "Fully Issued"
ITEM_STATUS_PARTIALLY_ISSUED = "Partially Issued"
ITEM_STATUS_CANCELLED = "Item Cancelled" # If an individual item line is cancelled

ALL_INDENT_ITEM_STATUSES = [
    ITEM_STATUS_PENDING_ISSUE, ITEM_STATUS_FULLY_ISSUED,
    ITEM_STATUS_PARTIALLY_ISSUED, ITEM_STATUS_CANCELLED
]