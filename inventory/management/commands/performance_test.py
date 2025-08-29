"""
Performance testing command to benchmark query performance
"""
import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import RequestFactory

from core.views import root_view
from inventory.models import Item, StockTransaction, Supplier
from inventory.views.items import ItemsTableView
from inventory.views.stock import history_reports
from inventory.views.suppliers import SuppliersTableView


class Command(BaseCommand):
    help = 'Run performance benchmarks on key application views'

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=5,
            help='Number of iterations for each test'
        )

    def handle(self, *args, **options):
        iterations = options['iterations']
        factory = RequestFactory()

        # Create a test user for authenticated views
        user = User.objects.filter(username='admin').first()
        if not user:
            self.stdout.write(
                self.style.WARNING('No admin user found, creating one...')
            )
            user = User.objects.create_superuser(
                'testuser', 'test@example.com', 'testpass'
            )

        self.stdout.write(
            f'🚀 Starting performance benchmarks '
            f'({iterations} iterations each)...\n'
        )

        # Test dashboard performance
        self.stdout.write('📊 Testing Dashboard Performance...')
        dashboard_times = []
        for i in range(iterations):
            start_time = time.time()
            query_count_start = len(connection.queries)

            request = factory.get('/')
            request.user = user
            _ = root_view(request)

            end_time = time.time()
            query_count_end = len(connection.queries)

            response_time = (end_time - start_time) * 1000
            query_count = query_count_end - query_count_start
            dashboard_times.append((response_time, query_count))

        avg_time = sum(t[0] for t in dashboard_times) / len(dashboard_times)
        avg_queries = sum(t[1] for t in dashboard_times) / len(dashboard_times)
        self.stdout.write(f'   Average: {avg_time:.1f}ms, {avg_queries:.1f} queries')

        # Test items list performance
        self.stdout.write('📋 Testing Items List Performance...')
        items_times = []
        for i in range(iterations):
            start_time = time.time()
            query_count_start = len(connection.queries)

            request = factory.get('/inventory/items/table/')
            request.user = user
            view = ItemsTableView.as_view()
            _ = view(request)

            end_time = time.time()
            query_count_end = len(connection.queries)

            response_time = (end_time - start_time) * 1000
            query_count = query_count_end - query_count_start
            items_times.append((response_time, query_count))

        avg_time = sum(t[0] for t in items_times) / len(items_times)
        avg_queries = sum(t[1] for t in items_times) / len(items_times)
        self.stdout.write(f'   Average: {avg_time:.1f}ms, {avg_queries:.1f} queries')

        # Test stock history performance
        self.stdout.write('📈 Testing Stock History Performance...')
        history_times = []
        for i in range(iterations):
            start_time = time.time()
            query_count_start = len(connection.queries)

            request = factory.get('/inventory/stock/history/')
            request.user = user
            _ = history_reports(request)

            end_time = time.time()
            query_count_end = len(connection.queries)

            response_time = (end_time - start_time) * 1000
            query_count = query_count_end - query_count_start
            history_times.append((response_time, query_count))

        avg_time = sum(t[0] for t in history_times) / len(history_times)
        avg_queries = sum(t[1] for t in history_times) / len(history_times)
        self.stdout.write(f'   Average: {avg_time:.1f}ms, {avg_queries:.1f} queries')

        # Test suppliers list performance
        self.stdout.write('🏢 Testing Suppliers List Performance...')
        suppliers_times = []
        for i in range(iterations):
            start_time = time.time()
            query_count_start = len(connection.queries)

            request = factory.get('/inventory/suppliers/table/')
            request.user = user
            view = SuppliersTableView.as_view()
            _ = view(request)  # call view; response unused

            end_time = time.time()
            query_count_end = len(connection.queries)

            response_time = (end_time - start_time) * 1000
            query_count = query_count_end - query_count_start
            suppliers_times.append((response_time, query_count))

        avg_time = sum(t[0] for t in suppliers_times) / len(suppliers_times)
        avg_queries = sum(t[1] for t in suppliers_times) / len(suppliers_times)
        self.stdout.write(f'   Average: {avg_time:.1f}ms, {avg_queries:.1f} queries')

        # Database statistics
        self.stdout.write('\n📊 Database Statistics:')
        self.stdout.write(f'   Total Items: {Item.objects.count()}')
        self.stdout.write(
            f'   Total Stock Transactions: '
            f'{StockTransaction.objects.count()}'
        )
        self.stdout.write(f'   Total Suppliers: {Supplier.objects.count()}')

        # Performance Summary
        self.stdout.write('\n🎯 Performance Summary:')
        total_avg_time = (
            sum(t[0] for t in dashboard_times) +
            sum(t[0] for t in items_times) +
            sum(t[0] for t in history_times) +
            sum(t[0] for t in suppliers_times)
        ) / (4 * iterations)

        total_avg_queries = (
            sum(t[1] for t in dashboard_times) +
            sum(t[1] for t in items_times) +
            sum(t[1] for t in history_times) +
            sum(t[1] for t in suppliers_times)
        ) / (4 * iterations)

        self.stdout.write(f'   Overall Average Response Time: {total_avg_time:.1f}ms')
        self.stdout.write(
            f'   Overall Average Query Count: {total_avg_queries:.1f} queries'
        )

        # Performance grades
        if total_avg_time < 100:
            grade = '🟢 EXCELLENT'
        elif total_avg_time < 200:
            grade = '🟡 GOOD'
        elif total_avg_time < 500:
            grade = '🟠 FAIR'
        else:
            grade = '🔴 NEEDS IMPROVEMENT'

        self.stdout.write(f'   Performance Grade: {grade}')

        self.stdout.write('\n✅ Performance benchmark complete!')

        if total_avg_queries > 15:
            self.stdout.write('\n💡 Optimization Suggestions:')
            self.stdout.write('   - Consider adding more database indexes')
            self.stdout.write('   - Implement query result caching')
            self.stdout.write(
                '   - Use select_related/prefetch_related for relationships'
            )

        if total_avg_time > 200:
            self.stdout.write('\n⚡ Speed Improvement Suggestions:')
            self.stdout.write('   - Enable Redis caching')
            self.stdout.write('   - Optimize database queries')
            self.stdout.write('   - Consider database connection pooling')
