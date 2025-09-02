class ServiceError(Exception):
    """Base class for inventory service layer exceptions."""


class SupplierServiceError(ServiceError):
    """Raised for errors in the supplier service."""


class PurchaseOrderServiceError(ServiceError):
    """Raised for errors in the purchase order service."""


class StockServiceError(ServiceError):
    """Raised for errors in the stock service."""
