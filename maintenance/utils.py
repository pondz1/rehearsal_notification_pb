# utils.py
from django.utils import timezone
from .models import PurchaseOrder

def generate_po_number():
    """
    Generate PO number in format: PO-YYMM-XXXX
    Example: PO-2404-0001
    """
    prefix = "PO"
    current_date = timezone.now()
    year = current_date.strftime('%y')
    month = current_date.strftime('%m')
    year_month = f"{year}{month}"

    # Get the latest PO number for this month
    latest_po = PurchaseOrder.objects.filter(
        po_number__startswith=f"{prefix}-{year_month}"
    ).order_by('-po_number').first()

    if latest_po:
        # Extract the running number from the latest PO number
        try:
            latest_number = int(latest_po.po_number.split('-')[-1])
            new_number = latest_number + 1
        except (ValueError, IndexError):
            # If there's an error parsing the number, start from 1
            new_number = 1
    else:
        # If no PO exists for this month, start from 1
        new_number = 1

    # Format: PO-YYMM-XXXX
    po_number = f"{prefix}-{year_month}-{new_number:04d}"

    # Verify uniqueness
    while PurchaseOrder.objects.filter(po_number=po_number).exists():
        new_number += 1
        po_number = f"{prefix}-{year_month}-{new_number:04d}"

    return po_number
