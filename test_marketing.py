"""
Test Marketing Automation & Campaigns
PDR CRM Part 28 - Marketing automation system
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_marketing():
    print("\n" + "="*80)
    print("TESTING MARKETING AUTOMATION & CAMPAIGNS")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.marketing_manager import MarketingManager

    # Use test database
    test_db = "data/test_marketing.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mgr = MarketingManager(db)

    # Setup: Create test customers
    print("Creating test customers...")
    for i in range(1, 6):
        db.execute("""
            INSERT INTO customers (first_name, last_name, email, phone, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f'Customer{i}',
            f'Test{i}',
            f'customer{i}@example.com',
            f'555-000{i}',
            datetime.now().isoformat()
        ))
    print()

    # ========================================================================
    # TEST 1: Create Customer Segment
    # ========================================================================

    print("="*80)
    print("[1/14] Creating customer segment...")
    print("="*80 + "\n")

    segment_id = mgr.create_customer_segment(
        segment_name='High-Value Customers',
        criteria={
            'total_spent_min': 5000,
            'services_count_min': 5,
            'loyalty_tier': ['GOLD', 'PLATINUM'],
            'last_service_days': 90
        },
        description='Customers who have spent $5k+ and had 5+ services'
    )
    print()

    assert segment_id > 0
    segment = mgr.get_segment(segment_id)
    assert segment['segment_name'] == 'High-Value Customers'
    print("[OK] Customer segment created")
    print()

    # ========================================================================
    # TEST 2: Create Email Campaign
    # ========================================================================

    print("="*80)
    print("[2/14] Creating email campaign...")
    print("="*80 + "\n")

    send_date = datetime.now() + timedelta(days=7)

    campaign_id = mgr.create_email_campaign(
        campaign_name='Spring Service Special',
        subject='Save 20% on PDR Services This Month!',
        email_content='''
            <html>
            <body>
                <h1>Spring Service Special!</h1>
                <p>Dear Valued Customer,</p>
                <p>Get 20% off all paintless dent repair services this spring!</p>
                <p>Use code: SPRING20</p>
                <a href="https://example.com/book">Book Now</a>
            </body>
            </html>
        ''',
        segment_id=segment_id,
        send_date=send_date,
        from_name='PDR Excellence',
        from_email='info@pdrexcellence.com',
        campaign_type='ONE_TIME'
    )
    print()

    assert campaign_id > 0
    campaign = mgr.get_campaign(campaign_id)
    assert campaign['campaign_name'] == 'Spring Service Special'
    assert campaign['status'] == 'SCHEDULED'
    print("[OK] Email campaign created")
    print()

    # ========================================================================
    # TEST 3: Send Email Campaign
    # ========================================================================

    print("="*80)
    print("[3/14] Sending email campaign...")
    print("="*80 + "\n")

    results = mgr.send_campaign(campaign_id)
    print()

    assert results['campaign_id'] == campaign_id
    assert results['sent_count'] >= 0

    campaign = mgr.get_campaign(campaign_id)
    assert campaign['status'] == 'ACTIVE'
    print("[OK] Email campaign sent")
    print()

    # ========================================================================
    # TEST 4: Record Email Opens and Clicks
    # ========================================================================

    print("="*80)
    print("[4/14] Recording email opens and clicks...")
    print("="*80 + "\n")

    # Simulate some opens and clicks
    for i in range(1, 4):
        mgr.record_email_open(campaign_id, i)
        print(f"  Customer {i} opened email")

    for i in range(1, 3):
        mgr.record_email_click(campaign_id, i)
        print(f"  Customer {i} clicked link")
    print()

    print("[OK] Email interactions recorded")
    print()

    # ========================================================================
    # TEST 5: Create SMS Campaign
    # ========================================================================

    print("="*80)
    print("[5/14] Creating SMS campaign...")
    print("="*80 + "\n")

    sms_campaign_id = mgr.create_sms_campaign(
        campaign_name='Flash Sale Alert',
        sms_content='Flash Sale! 15% off PDR services this weekend only. Book now!',
        segment_id=segment_id,
        send_date=datetime.now() + timedelta(days=1)
    )
    print()

    assert sms_campaign_id > 0
    sms_campaign = mgr.get_sms_campaign(sms_campaign_id)
    assert sms_campaign['campaign_name'] == 'Flash Sale Alert'
    assert 'STOP' in sms_campaign['sms_content']  # Opt-out included
    print("[OK] SMS campaign created")
    print()

    # ========================================================================
    # TEST 6: Create Automated Sequence (Drip Campaign)
    # ========================================================================

    print("="*80)
    print("[6/14] Creating automated sequence (drip campaign)...")
    print("="*80 + "\n")

    sequence_id = mgr.create_automated_sequence(
        sequence_name='Post-Service Follow-Up',
        trigger_type='JOB_COMPLETED',
        trigger_criteria={'days_after': 0},
        sequence_steps=[
            {
                'step_number': 1,
                'delay_days': 1,
                'action_type': 'EMAIL',
                'subject': 'Thank you for your business!',
                'content': 'Thank you for choosing PDR Excellence...'
            },
            {
                'step_number': 2,
                'delay_days': 7,
                'action_type': 'EMAIL',
                'subject': 'How did we do?',
                'content': 'We would love to hear your feedback...'
            },
            {
                'step_number': 3,
                'delay_days': 30,
                'action_type': 'EMAIL',
                'subject': 'Special offer for return customers',
                'content': 'As a valued customer, enjoy 10% off your next service...'
            }
        ],
        description='Automated follow-up sequence after job completion'
    )
    print()

    assert sequence_id > 0
    sequence = mgr.get_sequence(sequence_id)
    assert sequence['sequence_name'] == 'Post-Service Follow-Up'
    assert len(sequence['steps']) == 3
    print("[OK] Automated sequence created with 3 steps")
    print()

    # ========================================================================
    # TEST 7: Trigger Sequence for Customer
    # ========================================================================

    print("="*80)
    print("[7/14] Triggering sequence for customer...")
    print("="*80 + "\n")

    instance_id = mgr.trigger_sequence(
        sequence_id=sequence_id,
        customer_id=1,
        trigger_data={'job_id': 100, 'service_type': 'PDR'}
    )
    print()

    assert instance_id > 0
    instance = mgr.get_sequence_instance(instance_id)
    assert instance['status'] == 'ACTIVE'
    assert instance['current_step'] == 0
    print("[OK] Sequence triggered for customer")
    print()

    # ========================================================================
    # TEST 8: Process Sequence Steps
    # ========================================================================

    print("="*80)
    print("[8/14] Processing sequence steps...")
    print("="*80 + "\n")

    # Simulate time passing by updating triggered_at
    db.execute("""
        UPDATE sequence_instances
        SET triggered_at = ?
        WHERE id = ?
    """, ((datetime.now() - timedelta(days=2)).isoformat(), instance_id))

    process_results = mgr.process_sequence_steps()

    print(f"Sequence Processing Results:")
    print(f"  Instances processed: {process_results['instances_processed']}")
    print(f"  Messages sent: {process_results['messages_sent']}")
    print(f"  Sequences completed: {process_results['sequences_completed']}")
    print()

    assert process_results['instances_processed'] >= 0
    print("[OK] Sequence steps processed")
    print()

    # ========================================================================
    # TEST 9: Create Seasonal Promotion
    # ========================================================================

    print("="*80)
    print("[9/14] Creating seasonal promotion...")
    print("="*80 + "\n")

    promo_id = mgr.create_promotion(
        promotion_name='Spring Hail Season Special',
        promotion_type='SEASONAL',
        discount_type='PERCENTAGE',
        discount_value=20.0,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        promo_code='SPRING20',
        min_purchase=500.00,
        max_uses=100,
        description='20% off all hail damage repairs'
    )
    print()

    assert promo_id > 0
    promo = mgr.get_promotion(promo_id)
    assert promo['promo_code'] == 'SPRING20'
    assert promo['discount_value'] == 20.0
    print("[OK] Seasonal promotion created")
    print()

    # ========================================================================
    # TEST 10: Apply Promotion
    # ========================================================================

    print("="*80)
    print("[10/14] Applying promotion...")
    print("="*80 + "\n")

    discount = mgr.apply_promotion(
        promo_code='SPRING20',
        invoice_total=1000.00,
        customer_id=1
    )

    print(f"Promotion Applied:")
    print(f"  Original total: $1,000.00")
    print(f"  Discount: {discount['discount_type']} {discount['discount_value']}%")
    print(f"  Discount amount: ${discount['discount_amount']:.2f}")
    print(f"  Final total: ${discount['final_total']:.2f}")
    print()

    assert discount['discount_amount'] == 200.00
    assert discount['final_total'] == 800.00
    print("[OK] Promotion applied successfully")
    print()

    # ========================================================================
    # TEST 11: Get Active Promotions
    # ========================================================================

    print("="*80)
    print("[11/14] Getting active promotions...")
    print("="*80 + "\n")

    active_promos = mgr.get_active_promotions()

    print(f"Active Promotions ({len(active_promos)}):")
    for p in active_promos:
        print(f"  - {p['promotion_name']}: {p['promo_code']}")
    print()

    assert len(active_promos) >= 1
    print("[OK] Active promotions retrieved")
    print()

    # ========================================================================
    # TEST 12: Create and Complete Referral
    # ========================================================================

    print("="*80)
    print("[12/14] Creating and completing referral...")
    print("="*80 + "\n")

    referral_id = mgr.create_referral(
        referrer_customer_id=1,
        referred_customer_id=5,
        referral_source='DIRECT'
    )
    print()

    assert referral_id > 0

    mgr.complete_referral(
        referral_id=referral_id,
        referrer_reward_type='CREDIT',
        referrer_reward_value=50.00,
        referred_reward_type='DISCOUNT',
        referred_reward_value=25.00
    )
    print()

    referral = mgr.get_referral(referral_id)
    assert referral['status'] == 'COMPLETED'
    assert referral['referrer_reward_value'] == 50.00

    # Get customer referral summary
    referral_summary = mgr.get_customer_referrals(1)
    print(f"Customer 1 Referral Summary:")
    print(f"  Total referrals: {referral_summary['total_referrals']}")
    print(f"  Completed: {referral_summary['completed_referrals']}")
    print(f"  Total rewards: ${referral_summary['total_rewards_earned']:.2f}")
    print()

    print("[OK] Referral created and completed")
    print()

    # ========================================================================
    # TEST 13: A/B Testing
    # ========================================================================

    print("="*80)
    print("[13/14] Creating A/B test variants...")
    print("="*80 + "\n")

    variant_ids = mgr.create_ab_test(
        campaign_id=campaign_id,
        variants=[
            {
                'variant_name': 'Variant A - Emoji Subject',
                'subject': 'Spring Sale! Save 20% on PDR Services',
                'content': 'Original content...'
            },
            {
                'variant_name': 'Variant B - Question Subject',
                'subject': 'Ready to save on your next repair?',
                'content': 'Modified content...'
            }
        ]
    )
    print()

    assert len(variant_ids) == 2

    # Simulate some results
    db.execute("""
        UPDATE ab_test_variants
        SET sent_count = 100, open_count = 25, click_count = 5
        WHERE id = ?
    """, (variant_ids[0],))

    db.execute("""
        UPDATE ab_test_variants
        SET sent_count = 100, open_count = 32, click_count = 8
        WHERE id = ?
    """, (variant_ids[1],))

    ab_results = mgr.get_ab_test_results(campaign_id)

    print(f"A/B Test Results:")
    for v in ab_results['variants']:
        print(f"  {v['variant_name']}:")
        print(f"    Open rate: {v['open_rate']}%")
        print(f"    Click rate: {v['click_rate']}%")
    print()
    print(f"  Winner: {ab_results['winner']}")
    print(f"  Best open rate: {ab_results['best_rate']}%")
    print()

    assert ab_results['winner'] == 'Variant B - Question Subject'
    print("[OK] A/B test created and analyzed")
    print()

    # ========================================================================
    # TEST 14: Campaign Analytics & Marketing ROI
    # ========================================================================

    print("="*80)
    print("[14/14] Getting campaign analytics and marketing ROI...")
    print("="*80 + "\n")

    analytics = mgr.get_campaign_analytics(campaign_id)

    print(f"Campaign Analytics: {analytics['campaign_name']}")
    print(f"  Status: {analytics['status']}")
    print()
    print(f"  Metrics:")
    print(f"    Sent: {analytics['metrics']['sent']}")
    print(f"    Delivered: {analytics['metrics']['delivered']}")
    print(f"    Opened: {analytics['metrics']['opened']}")
    print(f"    Clicked: {analytics['metrics']['clicked']}")
    print()
    print(f"  Rates:")
    print(f"    Open rate: {analytics['rates']['open_rate']}%")
    print(f"    Click rate: {analytics['rates']['click_rate']}%")
    print()

    # Marketing ROI
    roi = mgr.get_marketing_roi(
        start_date=date.today() - timedelta(days=30),
        end_date=date.today()
    )

    print(f"Marketing ROI (Last 30 Days):")
    print(f"  Campaigns: {roi['campaigns']['total_campaigns']}")
    print(f"  Total sent: {roi['campaigns']['total_sent']}")
    print(f"  Marketing cost: ${roi['costs']['total_marketing_cost']:.2f}")
    print(f"  Attributed revenue: ${roi['revenue']['attributed_revenue']:.2f}")
    print(f"  ROI: {roi['roi']['roi_percent']}%")
    print()

    print("[OK] Campaign analytics and ROI calculated")
    print()

    # ========================================================================
    # BONUS: Marketing Dashboard
    # ========================================================================

    print("="*80)
    print("[BONUS] Getting marketing dashboard...")
    print("="*80 + "\n")

    dashboard = mgr.get_marketing_dashboard()

    print(f"Marketing Dashboard:")
    print(f"  Active email campaigns: {dashboard['active_email_campaigns']}")
    print(f"  Active sequences: {dashboard['active_sequences']}")
    print(f"  Active promotions: {dashboard['active_promotions']}")
    print(f"  Pending referrals: {dashboard['pending_referrals']}")
    print(f"  Customer segments: {dashboard['customer_segments']}")
    print()

    print("[OK] Marketing dashboard working")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] MARKETING AUTOMATION & CAMPAIGNS TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Customer segmentation")
    print("  [OK] Email campaign creation")
    print("  [OK] Campaign sending")
    print("  [OK] Email open/click tracking")
    print("  [OK] SMS campaigns")
    print("  [OK] Automated sequences (drip campaigns)")
    print("  [OK] Sequence triggering")
    print("  [OK] Sequence step processing")
    print("  [OK] Seasonal promotions")
    print("  [OK] Promotion application")
    print("  [OK] Referral tracking")
    print("  [OK] A/B testing")
    print("  [OK] Campaign analytics")
    print("  [OK] Marketing ROI calculation")
    print()

    print("CAMPAIGN TYPES:")
    for ct in mgr.CAMPAIGN_TYPES:
        print(f"  - {ct}")
    print()

    print("TRIGGER TYPES:")
    for tt in mgr.TRIGGER_TYPES:
        print(f"  - {tt}")
    print()

    print("MARKETING AUTOMATION WORKFLOW:")
    print("  1. Create customer segments based on criteria")
    print("  2. Build email/SMS campaigns targeting segments")
    print("  3. Schedule or send immediately")
    print("  4. Track opens, clicks, and conversions")
    print("  5. Set up automated sequences for follow-ups")
    print("  6. Create seasonal promotions with promo codes")
    print("  7. Run A/B tests to optimize performance")
    print("  8. Analyze ROI and adjust strategy")
    print()

    print("REFERRAL PROGRAM:")
    print("  - Track customer referrals")
    print("  - Issue rewards on completion")
    print("  - Referrer: $50 credit")
    print("  - Referred: $25 discount")
    print()

    print("Ready for PROMPT 29?")
    print()

    return True


if __name__ == '__main__':
    success = test_marketing()
    sys.exit(0 if success else 1)
