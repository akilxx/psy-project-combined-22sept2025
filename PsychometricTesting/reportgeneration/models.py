# reportgeneration/models.py

from django.db import models
from testing.models import PsychometricTest  # Import your PsychometricTest model
from payment.models import Payment  # Import your PsychometricTest model
from django.core.exceptions import ValidationError


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
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='test_report'
    )
    # We assume report_content is a list of dictionaries, e.g.:
    # [
    #     {"trait": "neuroticism", "percentile": 99, "text": "Sample text."},
    #     {"trait": "extraversion", "percentile": 45, "text": "Some other text."},
    # ]
    report_content = models.JSONField(
        default=list,
        help_text='A list of dictionaries with keys: "trait", "percentile", "text".'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """
        Custom validation to ensure:
        1. The associated payment has a status of 'succeeded'.
        2. The report_content includes entries for all traits from the associated PsychometricTest.
        """
        super().clean()

        # Ensure the payment has a succeeded status.
        if self.payment.status != 'succeeded':
            raise ValidationError("TestReport can only be created for payments with a 'succeeded' status.")

        # Ensure the payment is linked to a test.
        if not self.payment.test:
            raise ValidationError("The associated Payment must have a PsychometricTest assigned.")

        # Get the list of expected traits and dimensions from the PsychometricTest.
        expected_traits = set()
        for trait in self.payment.test.traits:
            # Add the trait's name
            expected_traits.add(trait['name'])
            # Add each dimension associated with the trait
            for dimension in trait.get('dimensions', []):
                expected_traits.add(dimension)

        # Ensure the report_content is a list.
        if not isinstance(self.report_content, list):
            raise ValidationError("The report content must be a list of dictionaries.")

        # Extract the traits reported in the TestReport.
        reported_traits = {entry.get("trait") for entry in self.report_content if "trait" in entry}

        # Check if any expected trait is missing.
        missing_traits = expected_traits - reported_traits
        if missing_traits:
            raise ValidationError(
                f"TestReport is missing report entries for the following traits: {', '.join(missing_traits)}"
            )

    def __str__(self):
        return f"TestReport for Payment {self.payment.id}"
    