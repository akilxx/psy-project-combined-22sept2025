# reportgeneration/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone

from testing.models import TestResult
from reportgeneration.models import TestReport
from payment.models import UserSubscription
from payment.subscription_service import consume_allowance
from reportgeneration.services import generate_test_report


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_test_report(request, test_result_id):
    """
    Retrieve the TestReport for a specific TestResult.
    """
    try:
        result = TestResult.objects.get(uuid=test_result_id, user=request.user)
    except TestResult.DoesNotExist:
        return Response({"detail": "Test result not found."}, status=404)

    try:
        test_report = result.generated_report
    except TestReport.DoesNotExist:
        return Response({"detail": "Report not generated yet."}, status=404)

    # Determine access method for frontend display
    access_method = "unknown"
    if test_report.payment:
        access_method = "one_time_payment"
    elif test_report.ledger_entry:
        access_method = "subscription"

    data = {
        "report_id": test_report.id,
        "test_result_id": str(result.uuid),
        "report_content": test_report.report_content,
        "created_at": test_report.created_at.isoformat(),
        "access_method": access_method
    }
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unlock_report_with_subscription(request, test_result_id):
    """
    Consumes 1 credit (or validates unlimited access) to generate a report.
    """
    user = request.user

    try:
        test_result = TestResult.objects.get(uuid=test_result_id, user=user)
    except TestResult.DoesNotExist:
        return Response({"detail": "Test result not found."}, status=404)

    # Check if already generated
    if hasattr(test_result, 'generated_report'):
        return Response({
            "detail": "Report already generated.",
            "report_id": test_result.generated_report.id
        }, status=200)

    # Find active subscription
    subscription = UserSubscription.objects.filter(
        user=user,
        is_active=True,
        status=UserSubscription.STATUS_ACTIVE
    ).first()

    if not subscription:
        return Response(
            {"detail": "No active subscription found. Please upgrade or pay directly."},
            status=403
        )

    # Even if status is 'active', check if the period has actually ended
    if subscription.current_period_end and subscription.current_period_end < timezone.now():
        return Response(
            {"detail": "Your subscription period has expired. Please renew to continue."},
            status=403
        )


    try:
        with transaction.atomic():
            # consume_allowance now returns a ledger entry even for unlimited plans
            ledger_entry = consume_allowance(
                subscription=subscription,
                test=test_result.test,
                quantity=1
            )

            report = generate_test_report(
                test_result=test_result,
                ledger_entry=ledger_entry
            )

            if not report:
                raise ValueError("Report generation failed internally.")

        return Response({
            "detail": "Report unlocked successfully.",
            "report_id": report.id
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    except Exception as e:
        return Response({"detail": "An unexpected error occurred."}, status=500)