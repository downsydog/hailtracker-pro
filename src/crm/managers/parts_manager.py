"""
Parts Manager
Manage parts catalog, orders, and local supplier sourcing

PDR CRM Part 7 - Local Sourcing Made Easy!

SOLVES:
- Finding best local prices
- Tracking what's ordered vs received
- Managing return costs
- Linking parts to jobs

FEATURES:
- Parts catalog
- Email suppliers for quotes
- Order tracking
- Return cost management
- Supplier performance
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import json


class PartsManager:
    """
    Manage parts catalog and ordering

    Makes finding and ordering parts efficient!
    """

    def __init__(self, db):
        """Initialize parts manager with database connection"""
        self.db = db

    # ========================================================================
    # PARTS CATALOG
    # ========================================================================

    def add_part(
        self,
        description: str,
        part_number: Optional[str] = None,
        category: str = "BODY_PANEL",
        preferred_supplier: Optional[str] = None,
        supplier_part_number: Optional[str] = None,
        cost: Optional[float] = None,
        retail_price: Optional[float] = None,
        in_stock: int = 0,
        reorder_level: int = 0
    ) -> int:
        """
        Add part to catalog

        Args:
            description: Part description
            part_number: Your part number
            category: BODY_PANEL, TRIM, HARDWARE, PAINT, SUPPLIES
            preferred_supplier: Default supplier
            supplier_part_number: Supplier's part number
            cost: Your cost
            retail_price: What you charge customer
            in_stock: Current inventory
            reorder_level: Reorder when inventory hits this

        Returns:
            Part ID
        """
        part_data = {
            'part_number': part_number,
            'description': description,
            'category': category,
            'preferred_supplier': preferred_supplier,
            'supplier_part_number': supplier_part_number,
            'cost': cost,
            'retail_price': retail_price,
            'in_stock': in_stock,
            'reorder_level': reorder_level
        }

        part_id = self.db.insert('parts', part_data)

        print(f"[OK] Added part #{part_id}: {description}")
        if preferred_supplier:
            print(f"     Preferred supplier: {preferred_supplier}")
        if cost and retail_price:
            markup = ((retail_price - cost) / cost * 100)
            print(f"     Cost: ${cost:.2f} -> Retail: ${retail_price:.2f} ({markup:.0f}% markup)")

        return part_id

    def get_part(self, part_id: int) -> Optional[Dict]:
        """Get part by ID"""
        results = self.db.execute("""
            SELECT * FROM parts WHERE id = ? AND deleted_at IS NULL
        """, (part_id,))
        return results[0] if results else None

    def search_parts(
        self,
        search_term: Optional[str] = None,
        category: Optional[str] = None,
        needs_reorder: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search parts catalog

        Args:
            search_term: Search description or part number
            category: Filter by category
            needs_reorder: Parts below reorder level
        """
        query = """
            SELECT *
            FROM parts
            WHERE deleted_at IS NULL
        """

        params = []

        if search_term:
            query += """ AND (
                description LIKE ? OR
                part_number LIKE ? OR
                supplier_part_number LIKE ?
            )"""
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern] * 3)

        if category:
            query += " AND category = ?"
            params.append(category)

        if needs_reorder:
            query += " AND in_stock <= reorder_level AND reorder_level > 0"

        query += " ORDER BY description LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def update_part(self, part_id: int, data: Dict) -> bool:
        """Update part details"""
        return self.db.update('parts', part_id, data)

    def update_inventory(
        self,
        part_id: int,
        quantity_change: int,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update part inventory

        Args:
            part_id: Part ID
            quantity_change: +5 to add, -3 to remove
            notes: Reason for change
        """
        self.db.execute("""
            UPDATE parts
            SET in_stock = in_stock + ?,
                updated_at = ?
            WHERE id = ?
        """, (quantity_change, datetime.now().isoformat(), part_id))

        part = self.get_part(part_id)

        action = "Added" if quantity_change > 0 else "Removed"
        print(f"[OK] {action} {abs(quantity_change)} unit(s) of {part['description']}")
        print(f"     New stock level: {part['in_stock']}")

        if part['in_stock'] <= (part['reorder_level'] or 0) and (part['reorder_level'] or 0) > 0:
            print(f"     [!] REORDER NEEDED (at or below {part['reorder_level']} units)")

        return True

    def get_low_stock_parts(self) -> List[Dict]:
        """Get parts below reorder level"""
        return self.search_parts(needs_reorder=True)

    # ========================================================================
    # PART ORDERS
    # ========================================================================

    def create_order(
        self,
        supplier_name: str,
        job_id: Optional[int] = None,
        parts: Optional[List[Dict]] = None,
        supplier_email: Optional[str] = None,
        supplier_phone: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create parts order

        Args:
            supplier_name: Supplier name
            job_id: Job this order is for (optional)
            parts: List of parts needed
                [{'part_id': 123, 'description': 'Bumper', 'quantity': 1}, ...]
            supplier_email: Supplier email for quotes
            supplier_phone: Supplier phone

        Returns:
            Order ID
        """
        # Generate order number
        order_number = self._generate_order_number()

        order_data = {
            'order_number': order_number,
            'job_id': job_id,
            'supplier_name': supplier_name,
            'supplier_email': supplier_email,
            'supplier_phone': supplier_phone,
            'status': 'QUOTED',
            'parts_json': json.dumps(parts) if parts else None,
            'notes': notes,
            'quote_requested_date': date.today().isoformat()
        }

        order_id = self.db.insert('part_orders', order_data)

        print(f"[OK] Created order #{order_number} (ID: {order_id})")
        print(f"     Supplier: {supplier_name}")
        if parts:
            print(f"     Parts: {len(parts)} item(s)")
            for part in parts:
                print(f"       - {part.get('description')} (Qty: {part.get('quantity', 1)})")

        return order_id

    def _generate_order_number(self) -> str:
        """Generate unique order number: PO-2024-0001"""
        year = datetime.now().year

        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM part_orders
            WHERE order_number LIKE ?
        """, (f"PO-{year}-%",))

        count = result[0]['count'] + 1

        return f"PO-{year}-{count:04d}"

    def get_order(self, order_id: int) -> Optional[Dict]:
        """Get order details with job info"""
        query = """
            SELECT
                po.*,
                j.job_number
            FROM part_orders po
            LEFT JOIN jobs j ON j.id = po.job_id
            WHERE po.id = ?
        """

        results = self.db.execute(query, (order_id,))

        if not results:
            return None

        order = results[0]

        # Parse parts JSON
        if order.get('parts_json'):
            order['parts_list'] = json.loads(order['parts_json'])
        else:
            order['parts_list'] = []

        return order

    def update_order_status(
        self,
        order_id: int,
        status: str,
        quote_amount: Optional[float] = None,
        actual_amount: Optional[float] = None,
        expected_delivery_date: Optional[date] = None,
        actual_delivery_date: Optional[date] = None,
        return_cost: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update order status

        Status: QUOTED -> ORDERED -> SHIPPED -> RECEIVED -> RETURNED

        Args:
            order_id: Order ID
            status: New status
            quote_amount: Quote received amount
            actual_amount: Actual charged amount
            expected_delivery_date: Expected delivery
            actual_delivery_date: Actual delivery
            return_cost: Core charge or restocking fee
        """
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Build update data
        update_fields = ['status']
        update_values = [status]

        if quote_amount is not None:
            update_fields.append('quote_amount')
            update_values.append(quote_amount)

        if actual_amount is not None:
            update_fields.append('actual_amount')
            update_values.append(actual_amount)

        if expected_delivery_date is not None:
            update_fields.append('expected_delivery_date')
            update_values.append(expected_delivery_date.isoformat())

        if actual_delivery_date is not None:
            update_fields.append('actual_delivery_date')
            update_values.append(actual_delivery_date.isoformat())

        if return_cost is not None:
            update_fields.append('return_cost')
            update_values.append(return_cost)

        if notes is not None:
            update_fields.append('notes')
            update_values.append(notes)

        # Auto-set dates based on status
        if status == 'QUOTED':
            update_fields.append('quote_received_date')
            update_values.append(date.today().isoformat())
        elif status == 'ORDERED':
            update_fields.append('ordered_date')
            update_values.append(date.today().isoformat())

        update_fields.append('updated_at')
        update_values.append(datetime.now().isoformat())

        # Build query
        set_clauses = [f"{f} = ?" for f in update_fields]
        query = f"UPDATE part_orders SET {', '.join(set_clauses)} WHERE id = ?"
        update_values.append(order_id)

        self.db.execute(query, tuple(update_values))

        print(f"[OK] Updated order #{order['order_number']} status: {status}")

        # Update inventory when parts received
        if status == 'RECEIVED' and actual_delivery_date:
            parts = order.get('parts_list', [])
            for part in parts:
                if part.get('part_id'):
                    self.update_inventory(
                        part_id=part['part_id'],
                        quantity_change=part.get('quantity', 1),
                        notes=f"Received from order {order['order_number']}"
                    )

        return True

    def search_orders(
        self,
        status: Optional[str] = None,
        supplier_name: Optional[str] = None,
        job_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Search orders with filters"""
        query = """
            SELECT
                po.*,
                j.job_number
            FROM part_orders po
            LEFT JOIN jobs j ON j.id = po.job_id
            WHERE 1=1
        """

        params = []

        if status:
            query += " AND po.status = ?"
            params.append(status)

        if supplier_name:
            query += " AND po.supplier_name LIKE ?"
            params.append(f"%{supplier_name}%")

        if job_id:
            query += " AND po.job_id = ?"
            params.append(job_id)

        if start_date:
            query += " AND po.created_at >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND po.created_at <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY po.created_at DESC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def get_pending_orders(self) -> List[Dict]:
        """Get orders that haven't been received yet"""
        return self.search_orders(status='ORDERED')

    def get_orders_for_job(self, job_id: int) -> List[Dict]:
        """Get all orders for a specific job"""
        return self.search_orders(job_id=job_id)

    # ========================================================================
    # QUOTE MANAGEMENT (LOCAL SOURCING!)
    # ========================================================================

    def add_quote(
        self,
        order_id: int,
        supplier_name: str,
        quoted_price: float,
        quoted_delivery_days: Optional[int] = None,
        return_policy: Optional[str] = None,
        core_charge: Optional[float] = None,
        expires_date: Optional[date] = None
    ) -> int:
        """
        Add quote from supplier

        Args:
            order_id: Part order ID
            supplier_name: Supplier who quoted
            quoted_price: Quote amount
            quoted_delivery_days: Delivery time in days
            return_policy: Return policy details
            core_charge: Core charge if applicable
            expires_date: When quote expires

        Returns:
            Quote ID
        """
        quote_data = {
            'part_order_id': order_id,
            'supplier_name': supplier_name,
            'quoted_price': quoted_price,
            'quoted_delivery_days': quoted_delivery_days,
            'return_policy': return_policy,
            'core_charge': core_charge or 0.0,
            'quote_received_at': datetime.now().isoformat(),
            'quote_expires_at': expires_date.isoformat() if expires_date else None,
            'selected': 0
        }

        quote_id = self.db.insert('part_quotes', quote_data)

        print(f"[OK] Added quote from {supplier_name}: ${quoted_price:,.2f}")
        if quoted_delivery_days:
            print(f"     Delivery: {quoted_delivery_days} day(s)")
        if core_charge:
            print(f"     Core charge: ${core_charge:,.2f}")

        return quote_id

    def get_quote(self, quote_id: int) -> Optional[Dict]:
        """Get quote by ID"""
        results = self.db.execute("""
            SELECT * FROM part_quotes WHERE id = ?
        """, (quote_id,))
        return results[0] if results else None

    def get_order_quotes(self, order_id: int) -> List[Dict]:
        """Get all quotes for an order, sorted by price"""
        query = """
            SELECT *
            FROM part_quotes
            WHERE part_order_id = ?
            ORDER BY quoted_price ASC
        """

        return self.db.execute(query, (order_id,))

    def select_quote(self, quote_id: int) -> bool:
        """
        Select winning quote

        Marks this quote as selected and updates order
        """
        # Get quote
        quote = self.get_quote(quote_id)
        if not quote:
            raise ValueError(f"Quote {quote_id} not found")

        # Mark as selected
        self.db.execute("""
            UPDATE part_quotes
            SET selected = 1
            WHERE id = ?
        """, (quote_id,))

        # Unselect other quotes for same order
        self.db.execute("""
            UPDATE part_quotes
            SET selected = 0
            WHERE part_order_id = ? AND id != ?
        """, (quote['part_order_id'], quote_id))

        # Update order with selected quote info
        expected_delivery = None
        if quote['quoted_delivery_days']:
            expected_delivery = (date.today() + timedelta(days=quote['quoted_delivery_days'])).isoformat()

        self.db.execute("""
            UPDATE part_orders
            SET supplier_name = ?,
                quote_amount = ?,
                expected_delivery_date = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            quote['supplier_name'],
            quote['quoted_price'],
            expected_delivery,
            datetime.now().isoformat(),
            quote['part_order_id']
        ))

        print(f"[OK] Selected quote from {quote['supplier_name']}")
        print(f"     Price: ${quote['quoted_price']:,.2f}")
        if quote['quoted_delivery_days']:
            print(f"     Expected delivery: {expected_delivery}")

        return True

    def generate_quote_comparison(self, order_id: int) -> str:
        """
        Generate quote comparison report

        Returns formatted string comparing all quotes for an order
        """
        order = self.get_order(order_id)
        if not order:
            return "Order not found"

        quotes = self.get_order_quotes(order_id)

        if not quotes:
            return "No quotes received yet"

        lines = []
        lines.append("=" * 70)
        lines.append("                    QUOTE COMPARISON")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Order: {order['order_number']}")
        if order.get('job_number'):
            lines.append(f"Job: {order['job_number']}")
        lines.append("")

        # List parts
        lines.append("Parts Requested:")
        for part in order.get('parts_list', []):
            lines.append(f"  - {part.get('description')} (Qty: {part.get('quantity', 1)})")
        lines.append("")

        lines.append("-" * 70)
        lines.append("")

        # Show each quote
        for i, quote in enumerate(quotes, 1):
            selected = " [SELECTED]" if quote['selected'] else ""

            lines.append(f"{i}. {quote['supplier_name']}{selected}")
            lines.append(f"   Price: ${quote['quoted_price']:,.2f}")

            if quote['quoted_delivery_days']:
                lines.append(f"   Delivery: {quote['quoted_delivery_days']} day(s)")

            if quote['core_charge']:
                lines.append(f"   Core charge: ${quote['core_charge']:,.2f}")

            if quote['return_policy']:
                lines.append(f"   Return policy: {quote['return_policy']}")

            # Calculate total cost
            total = quote['quoted_price'] + (quote['core_charge'] or 0)
            lines.append(f"   TOTAL COST: ${total:,.2f}")
            lines.append("")

        lines.append("-" * 70)

        # Show best price
        best_quote = min(quotes, key=lambda q: q['quoted_price'])
        lines.append("")
        lines.append(f"BEST PRICE: {best_quote['supplier_name']} at ${best_quote['quoted_price']:,.2f}")
        lines.append("")

        return '\n'.join(lines)

    # ========================================================================
    # EMAIL QUOTE REQUEST (AUTOMATION!)
    # ========================================================================

    def generate_quote_request_email(
        self,
        order_id: int,
        supplier_name: str,
        supplier_email: str
    ) -> Dict[str, str]:
        """
        Generate email to send to supplier for quote

        Returns email template ready to send
        """
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        parts = order.get('parts_list', [])

        subject = f"Quote Request - Order {order['order_number']}"

        body = f"""Hello {supplier_name},

We need a quote for the following parts:

Order Number: {order['order_number']}
"""

        if order.get('job_number'):
            body += f"Job: {order['job_number']}\n"

        body += "\nPARTS NEEDED:\n\n"

        for i, part in enumerate(parts, 1):
            body += f"{i}. {part.get('description')}\n"
            body += f"   Quantity: {part.get('quantity', 1)}\n"
            if part.get('supplier_part_number'):
                body += f"   Part Number: {part.get('supplier_part_number')}\n"
            body += "\n"

        body += """Please provide:
1. Price per part
2. Total price
3. Availability/delivery time
4. Any core charges or return fees

Please respond by email or call us at your earliest convenience.

Thank you,
PDR Shop
"""

        return {
            'to': supplier_email,
            'subject': subject,
            'body': body,
            'order_id': order_id,
            'order_number': order['order_number']
        }

    def generate_multi_supplier_quotes(
        self,
        order_id: int,
        suppliers: List[Dict]
    ) -> List[Dict]:
        """
        Generate quote request emails for multiple suppliers

        Args:
            order_id: Order ID
            suppliers: List of {'name': 'xxx', 'email': 'xxx@xxx.com'}

        Returns:
            List of email templates
        """
        emails = []
        for supplier in suppliers:
            email = self.generate_quote_request_email(
                order_id=order_id,
                supplier_name=supplier['name'],
                supplier_email=supplier['email']
            )
            emails.append(email)

        print(f"[OK] Generated {len(emails)} quote request emails")
        for email in emails:
            print(f"     - {email['to']}")

        return emails

    # ========================================================================
    # JOB PARTS TRACKING
    # ========================================================================

    def get_parts_needed_for_job(self, job_id: int) -> Dict:
        """
        Get parts status for a job

        Returns summary of parts ordered, received, pending
        """
        orders = self.get_orders_for_job(job_id)

        summary = {
            'total_orders': len(orders),
            'total_quoted': 0,
            'total_spent': 0,
            'parts_pending': [],
            'parts_received': [],
            'orders': orders
        }

        for order in orders:
            if order.get('quote_amount'):
                summary['total_quoted'] += order['quote_amount']
            if order.get('actual_amount'):
                summary['total_spent'] += order['actual_amount']

            parts = json.loads(order['parts_json']) if order.get('parts_json') else []

            if order['status'] == 'RECEIVED':
                summary['parts_received'].extend(parts)
            elif order['status'] in ('QUOTED', 'ORDERED', 'SHIPPED'):
                summary['parts_pending'].extend(parts)

        return summary

    # ========================================================================
    # STATISTICS & REPORTING
    # ========================================================================

    def get_parts_stats(self) -> Dict:
        """Get parts statistics for dashboard"""
        stats = {}

        # Total parts in catalog
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM parts
            WHERE deleted_at IS NULL
        """)
        stats['total_parts'] = result[0]['count']

        # Parts needing reorder
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM parts
            WHERE deleted_at IS NULL
              AND in_stock <= reorder_level
              AND reorder_level > 0
        """)
        stats['needs_reorder'] = result[0]['count']

        # Total inventory value
        result = self.db.execute("""
            SELECT SUM(in_stock * cost) as value
            FROM parts
            WHERE deleted_at IS NULL AND cost IS NOT NULL
        """)
        stats['inventory_value'] = result[0]['value'] or 0

        # Order statistics
        result = self.db.execute("""
            SELECT
                COUNT(*) as count,
                SUM(quote_amount) as total_quoted,
                SUM(actual_amount) as total_spent,
                SUM(return_cost) as total_returns
            FROM part_orders
        """)
        stats['total_orders'] = result[0]['count'] or 0
        stats['total_quoted'] = result[0]['total_quoted'] or 0
        stats['total_spent'] = result[0]['total_spent'] or 0
        stats['total_returns'] = result[0]['total_returns'] or 0

        # Orders by status
        result = self.db.execute("""
            SELECT status, COUNT(*) as count
            FROM part_orders
            GROUP BY status
        """)
        stats['by_status'] = {row['status']: row['count'] for row in result}

        # This month's spending
        result = self.db.execute("""
            SELECT SUM(actual_amount) as total
            FROM part_orders
            WHERE strftime('%Y-%m', ordered_date) = strftime('%Y-%m', 'now')
        """)
        stats['month_spending'] = result[0]['total'] or 0

        return stats

    def get_supplier_performance(self) -> List[Dict]:
        """
        Get supplier performance metrics

        Shows which suppliers are fastest, cheapest, most reliable
        """
        query = """
            SELECT
                supplier_name,
                COUNT(*) as order_count,
                AVG(quote_amount) as avg_quote,
                AVG(actual_amount) as avg_actual,
                AVG(JULIANDAY(actual_delivery_date) - JULIANDAY(ordered_date)) as avg_delivery_days,
                SUM(CASE WHEN status = 'RECEIVED' THEN 1 ELSE 0 END) as completed_orders,
                SUM(return_cost) as total_return_costs
            FROM part_orders
            WHERE supplier_name IS NOT NULL
            GROUP BY supplier_name
            ORDER BY order_count DESC
        """

        results = self.db.execute(query)

        # Calculate reliability score
        for supplier in results:
            if supplier['order_count'] > 0:
                supplier['reliability_pct'] = round(
                    (supplier['completed_orders'] / supplier['order_count']) * 100, 1
                )
            else:
                supplier['reliability_pct'] = 0

        return results

    def get_category_summary(self) -> List[Dict]:
        """Get parts summary by category"""
        query = """
            SELECT
                category,
                COUNT(*) as part_count,
                SUM(in_stock) as total_stock,
                SUM(in_stock * cost) as stock_value,
                SUM(CASE WHEN in_stock <= reorder_level AND reorder_level > 0 THEN 1 ELSE 0 END) as needs_reorder
            FROM parts
            WHERE deleted_at IS NULL
            GROUP BY category
            ORDER BY stock_value DESC
        """

        return self.db.execute(query)

    def format_parts_report(self, days: int = 30) -> str:
        """Generate formatted parts report"""
        stats = self.get_parts_stats()
        suppliers = self.get_supplier_performance()

        lines = []
        lines.append("=" * 70)
        lines.append("                    PARTS MANAGEMENT REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Inventory summary
        lines.append("INVENTORY SUMMARY:")
        lines.append(f"  Total parts in catalog: {stats['total_parts']}")
        lines.append(f"  Inventory value: ${stats['inventory_value']:,.2f}")
        lines.append(f"  Parts needing reorder: {stats['needs_reorder']}")
        lines.append("")

        # Order summary
        lines.append("ORDER SUMMARY:")
        lines.append(f"  Total orders: {stats['total_orders']}")
        lines.append(f"  Total quoted: ${stats['total_quoted']:,.2f}")
        lines.append(f"  Total spent: ${stats['total_spent']:,.2f}")
        lines.append(f"  Return costs: ${stats['total_returns']:,.2f}")
        lines.append(f"  This month: ${stats['month_spending']:,.2f}")
        lines.append("")

        # Orders by status
        lines.append("  By Status:")
        for status, count in stats.get('by_status', {}).items():
            lines.append(f"    {status}: {count}")
        lines.append("")

        # Supplier performance
        if suppliers:
            lines.append("-" * 70)
            lines.append("SUPPLIER PERFORMANCE:")
            lines.append("")

            for supplier in suppliers[:5]:  # Top 5 suppliers
                lines.append(f"  {supplier['supplier_name']}")
                lines.append(f"    Orders: {supplier['order_count']} ({supplier['completed_orders']} completed)")
                lines.append(f"    Reliability: {supplier['reliability_pct']}%")
                if supplier['avg_quote']:
                    lines.append(f"    Avg quote: ${supplier['avg_quote']:,.2f}")
                if supplier['avg_delivery_days']:
                    lines.append(f"    Avg delivery: {supplier['avg_delivery_days']:.1f} days")
                lines.append("")

        lines.append("=" * 70)

        return '\n'.join(lines)
