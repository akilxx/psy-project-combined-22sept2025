# reportgeneration/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from payment.models import Payment
from reportgeneration.models import TestReport

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_test_report(request, payment_id):
    """
    Retrieve the TestReport for the given Payment (identified by payment_id).
    Only authenticated users can access this view.
    """
    try:
        # Get the Payment object; payment_id is expected to be a UUID.
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return Response({"detail": "Payment not found."}, status=404)

    try:
        # Access the one-to-one related TestReport via the reverse relation.
        test_report = payment.test_report
    except TestReport.DoesNotExist:
        return Response({"detail": "TestReport not found for this Payment."}, status=404)

    data = {
        "payment_id": str(payment.id),
        "report_content": test_report.report_content,
        "created_at": test_report.created_at.isoformat(),
    }
    return Response(data)
