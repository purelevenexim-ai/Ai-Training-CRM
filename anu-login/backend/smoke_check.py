import sys
import os
from datetime import datetime

# Adjust path if needed
sys.path.append(os.getcwd())

try:
    from app.main import app
    from app.services.promotional_campaign_service import PromotionalCampaignService
    print("Import successful")

    # Create a campaign
    # Based on the grep output: name, template_type, subject, html_body
    campaign = PromotionalCampaignService.create_campaign(
        name="Smoke Test Campaign",
        template_type="email",
        subject="Smoke Test Subject",
        html_body="<p>Test Body</p>",
        segment="all"
    )
    print(f"Campaign created: {campaign.get('id')}")

    # Enqueue campaign
    if 'id' in campaign:
        enqueue_result = PromotionalCampaignService.enqueue_campaign(campaign['id'])
        print(f"Enqueue result keys: {list(enqueue_result.keys())}")
    else:
        print("Campaign ID not found in create_campaign result")

    # Process queue batch
    process_result = PromotionalCampaignService.process_queue_batch()
    print(f"Process result keys: {list(process_result.keys())}")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
