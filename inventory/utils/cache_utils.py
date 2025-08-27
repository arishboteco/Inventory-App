"""
Caching utilities for improved performance
"""
from django.core.cache import cache
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Item, StockTransaction, Supplier
import hashlib

# Cache timeout settings
CACHE_TIMEOUT_SHORT = 300  # 5 minutes
CACHE_TIMEOUT_MEDIUM = 900  # 15 minutes  
CACHE_TIMEOUT_LONG = 3600   # 1 hour

def get_cache_key(prefix, *args):
    """Generate a consistent cache key"""
    key_parts = [str(arg) for arg in args if arg is not None]
    key_string = f"{prefix}:{':'.join(key_parts)}"
    # Hash long keys to avoid cache key length limits
    if len(key_string) > 200:
        key_string = f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
    return key_string

def cache_item_details(item_id):
    """Cache item details for frequently accessed items"""
    cache_key = get_cache_key('item_detail', item_id)
    
    def get_item_details():
        try:
            from .services import item_service
            return item_service.get_item_details(item_id)
        except:
            return None
    
    return cache.get_or_set(cache_key, get_item_details, CACHE_TIMEOUT_MEDIUM)

def cache_dashboard_stats():
    """Cache dashboard statistics"""
    cache_key = get_cache_key('dashboard_stats')
    
    def get_dashboard_stats():
        from .models import Item, StockTransaction
        from django.db.models import Count, Sum
        
        stats = {
            'total_items': Item.objects.filter(is_active=True).count(),
            'low_stock_items': Item.objects.filter(
                is_active=True,
                current_stock__lt=F('reorder_point')
            ).count(),
            'recent_transactions': StockTransaction.objects.count(),
        }
        return stats
    
    return cache.get_or_set(cache_key, get_dashboard_stats, CACHE_TIMEOUT_SHORT)

def cache_transaction_types():
    """Cache transaction types for filters"""
    cache_key = get_cache_key('transaction_types')
    
    def get_transaction_types():
        return list(
            StockTransaction.objects
            .values_list("transaction_type", flat=True)
            .order_by("transaction_type")
            .distinct()
        )
    
    return cache.get_or_set(cache_key, get_transaction_types, CACHE_TIMEOUT_LONG)

def cache_active_suppliers():
    """Cache active suppliers list"""
    cache_key = get_cache_key('active_suppliers')
    
    def get_active_suppliers():
        return list(
            Supplier.objects
            .filter(is_active=True)
            .values('supplier_id', 'name')
            .order_by('name')
        )
    
    return cache.get_or_set(cache_key, get_active_suppliers, CACHE_TIMEOUT_MEDIUM)

def invalidate_item_cache(item_id):
    """Invalidate cache for a specific item"""
    cache_keys = [
        get_cache_key('item_detail', item_id),
        get_cache_key('dashboard_stats'),
    ]
    cache.delete_many(cache_keys)

def invalidate_transaction_cache():
    """Invalidate transaction-related cache"""
    cache_keys = [
        get_cache_key('dashboard_stats'),
        get_cache_key('transaction_types'),
    ]
    cache.delete_many(cache_keys)

def invalidate_supplier_cache():
    """Invalidate supplier-related cache"""
    cache_keys = [
        get_cache_key('active_suppliers'),
    ]
    cache.delete_many(cache_keys)

# Signal handlers to invalidate cache when models change
@receiver(post_save, sender=Item)
@receiver(post_delete, sender=Item)
def item_cache_invalidation(sender, instance, **kwargs):
    invalidate_item_cache(instance.item_id)

@receiver(post_save, sender=StockTransaction)
@receiver(post_delete, sender=StockTransaction)
def transaction_cache_invalidation(sender, instance, **kwargs):
    invalidate_transaction_cache()
    if hasattr(instance, 'item_id'):
        invalidate_item_cache(instance.item_id)

@receiver(post_save, sender=Supplier)
@receiver(post_delete, sender=Supplier)
def supplier_cache_invalidation(sender, instance, **kwargs):
    invalidate_supplier_cache()
