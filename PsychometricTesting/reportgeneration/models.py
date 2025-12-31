# reportgeneration/models.py

from django.db import models
from django.core.exceptions import ValidationError
from testing.models import PsychometricTest, TestResult
from payment.models import Payment, TestAllowanceLedger


class ReportTemplate(models.Model):
    psychometric_test = models.OneToOneField(
        PsychometricTest,
        on_delete=models.CASCADE,
        related_name='report_template'
    )

    def __str__(self):
        return f"Report Template for {self.psychometric_test.test_name}"


class ContentBlock(models.Model):
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='content_blocks'
    )
    trait = models.CharField(max_length=255)
    percentile_lower_bound = models.IntegerField()
    percentile_upper_bound = models.IntegerField()
    content = models.TextField()

    def __str__(self):
        return f"Content Block for {self.report_template.psychometric_test.test_name} - Trait: {self.trait}"


class TestReport(models.Model):
    # Primary Link: The result this report describes
    test_result = models.OneToOneField(
        TestResult,
        on_delete=models.CASCADE,
        related_name='generated_report',
    )

    # Funding Source A: Direct Payment (Optional)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_report'
    )

    # Funding Source B: Subscription Allowance (Optional)
    ledger_entry = models.OneToOneField(
        TestAllowanceLedger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_report'
    )

    report_content = models.JSONField(
        default=list,
        help_text='A list of dictionaries with keys: "trait", "percentile", "text".'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()

        # 1. Validate Funding Source
        # We require either a succeeded payment OR a ledger entry
        has_valid_payment = self.payment and self.payment.status == 'succeeded'
        has_allowance = self.ledger_entry is not None

        if not (has_valid_payment or has_allowance):
            raise ValidationError(
                "TestReport must be linked to either a succeeded Payment or a Subscription Allowance (Ledger Entry)."
            )

        # 2. Validate Test Result
        if not self.test_result:
            raise ValidationError("TestReport must be linked to a TestResult.")

        # 3. Validate Content Completeness
        if not isinstance(self.report_content, list):
            raise ValidationError("The report content must be a list of dictionaries.")

        # Check if all expected traits are present
        test_instance = self.test_result.test
        expected_traits = set()
        for trait in test_instance.traits:
            expected_traits.add(trait['name'])
            for dimension in trait.get('dimensions', []):
                expected_traits.add(dimension)

        reported_traits = {entry.get("trait") for entry in self.report_content if "trait" in entry}
        missing_traits = expected_traits - reported_traits

        if missing_traits:
            raise ValidationError(
                f"TestReport is missing report entries for: {', '.join(missing_traits)}"
            )

    def __str__(self):
        return f"TestReport for Result {self.test_result.uuid}"