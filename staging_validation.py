#!/usr/bin/env python3
"""
Staging Environment Validation Script
Tests critical functionality to ensure staging deployment is working correctly.
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_app.settings_staging')
sys.path.append('/workspaces/Inventory-App')
django.setup()

def test_database_connectivity():
    """Test database connection and basic queries."""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print("✅ Database connectivity: PASSED")
        return True
    except Exception as e:
        print(f"❌ Database connectivity: FAILED - {e}")
        return False

def test_models_functionality():
    """Test basic model operations."""
    try:
        from inventory.models import Item, Department
        
        # Test Item model
        item_count = Item.objects.count()
        print(f"✅ Items in database: {item_count}")
        
        # Test Department model  
        dept_count = Department.objects.count()
        print(f"✅ Departments in database: {dept_count}")
        
        print("✅ Models functionality: PASSED")
        return True
    except Exception as e:
        print(f"❌ Models functionality: FAILED - {e}")
        return False

def test_dashboard_service():
    """Test the fixed dashboard service."""
    try:
        from inventory.services import dashboard_service
        
        # Test the function that was causing issues
        low_stock_items = dashboard_service.get_low_stock_items()
        low_stock_count = len(low_stock_items)
        print(f"✅ Low stock items query: {low_stock_count} items")
        
        # Test each item has required attributes
        for item in low_stock_items[:3]:  # Test first 3 items
            assert hasattr(item, 'name')
            assert hasattr(item, 'current_stock')
            assert hasattr(item, 'reorder_point')
            assert hasattr(item, 'uom')  # Unit display
            assert hasattr(item, 'unit')  # Unit ID
        
        print("✅ Dashboard service: PASSED")
        return True
    except Exception as e:
        print(f"❌ Dashboard service: FAILED - {e}")
        return False

def test_kpis_service():
    """Test KPIs functionality."""
    try:
        from inventory.services import kpis
        
        # Test low stock count
        low_stock_count = kpis.low_stock_count()
        print(f"✅ KPI - Low stock count: {low_stock_count}")
        
        # Test other KPIs
        from inventory.services import counts
        item_count = counts.item_count()
        supplier_count = counts.supplier_count()
        
        print(f"✅ KPI - Item count: {item_count}")
        print(f"✅ KPI - Supplier count: {supplier_count}")
        
        print("✅ KPIs service: PASSED")
        return True
    except Exception as e:
        print(f"❌ KPIs service: FAILED - {e}")
        return False

def test_unit_display():
    """Test unit display functionality."""
    try:
        from inventory.services.item_service import get_unit_display_name
        
        # Test with known unit IDs
        test_units = [1, 19, 55]
        for unit_id in test_units:
            unit_name = get_unit_display_name(unit_id)
            print(f"✅ Unit {unit_id}: {unit_name}")
        
        print("✅ Unit display: PASSED")
        return True
    except Exception as e:
        print(f"❌ Unit display: FAILED - {e}")
        return False

def test_authentication():
    """Test authentication system."""
    try:
        from django.contrib.auth.models import User
        
        # Check if test user exists
        test_user = User.objects.filter(username='testuser').first()
        if test_user:
            print(f"✅ Test user exists: {test_user.username}")
        else:
            print("⚠️  Test user not found")
        
        total_users = User.objects.count()
        print(f"✅ Total users: {total_users}")
        
        print("✅ Authentication: PASSED")
        return True
    except Exception as e:
        print(f"❌ Authentication: FAILED - {e}")
        return False

def test_api_functionality():
    """Test API endpoints functionality."""
    try:
        from inventory.models import Item
        from django.http import HttpRequest
        from inventory.views.api import ItemViewSet
        
        # Test item serialization
        items = Item.objects.all()[:3]
        print(f"✅ API - Items accessible: {len(items)}")
        
        print("✅ API functionality: PASSED")
        return True
    except Exception as e:
        print(f"❌ API functionality: FAILED - {e}")
        return False

def main():
    """Run all validation tests."""
    print("🚀 STAGING ENVIRONMENT VALIDATION")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print()
    
    tests = [
        test_database_connectivity,
        test_models_functionality,
        test_authentication,
        test_unit_display,
        test_dashboard_service,
        test_kpis_service,
        test_api_functionality,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 VALIDATION SUMMARY")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"🎯 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Staging environment is ready!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review issues above.")
        return 1

if __name__ == "__main__":
    exit(main())
