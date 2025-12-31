#reportgeneration/admin.py

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from .models import ReportTemplate, ContentBlock, TestReport


# Custom inline formset to perform validations on the ContentBlocks.
class ContentBlockInlineFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()

        # Collect traits from the parent instance (if available)
        if self.instance:
            # Collect test traits from the associated psychometric_test
            test_traits = set()
            for trait in self.instance.psychometric_test.traits:
                test_traits.add(trait['name'])
                for dimension in trait.get('dimensions', []):
                    test_traits.add(dimension)

        # Gather traits provided in the inline ContentBlock forms.
        template_traits = set()
        for form in self.forms:
            # Only consider forms not marked for deletion.
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                template_traits.add(form.cleaned_data.get('trait'))

        if test_traits != template_traits:
            raise ValidationError("ReportTemplate must have and only have all traits in the PsychometricTest.")

        # Validate that each trait has an equal number of ContentBlocks.
        trait_counts = {trait: 0 for trait in test_traits}
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                trait = form.cleaned_data.get('trait')
                trait_counts[trait] += 1

        if len(set(trait_counts.values())) != 1:
            raise ValidationError("Each trait must have an equal number of ContentBlocks.")


# Inline admin for ContentBlock.
class ContentBlockInline(admin.TabularInline):
    model = ContentBlock
    formset = ContentBlockInlineFormset
    extra = 1


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    inlines = [ContentBlockInline]

    def get_inline_instances(self, request, obj=None):
        """
        Only display the inline ContentBlocks after the ReportTemplate instance is created.
        This forces a two-step creation process:
          1. Create and save the ReportTemplate with its associated psychometric_test.
          2. Edit the ReportTemplate to add ContentBlocks.
        """
        if obj is None:
            return []  # Do not show inlines when creating a new ReportTemplate.
        return super().get_inline_instances(request, obj)


@admin.register(TestReport)
class TestReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user', 'get_test_name', 'funding_source', 'created_at')
    list_filter = ('created_at',)

    # Updated search fields to include Payment ID and TestResult UUID
    search_fields = (
        'test_result__user__email',
        'test_result__test__test_name',
        'payment__stripe_payment_intent_id',
        'payment__id',
        'test_result__uuid'
    )

    readonly_fields = ('created_at', 'funding_source_display', 'report_content_display')
    exclude = ('report_content',)  # Exclude the raw JSON content from editable fields

    def get_user(self, obj):
        return obj.test_result.user.email if obj.test_result and obj.test_result.user else "Unknown"

    get_user.short_description = 'User'

    def get_test_name(self, obj):
        return obj.test_result.test.test_name if obj.test_result and obj.test_result.test else "Unknown"

    get_test_name.short_description = 'Test Name'

    def funding_source(self, obj):
        if obj.payment:
            return "Payment"
        elif obj.ledger_entry:
            return "Subscription"
        return "None"

    funding_source.short_description = 'Source'

    def funding_source_display(self, obj):
        """Helper to show the specific funding object in the detail view"""
        if obj.payment:
            return f"Payment ID: {obj.payment.id} (Stripe: {obj.payment.stripe_payment_intent_id})"
        elif obj.ledger_entry:
            return f"Ledger Entry ID: {obj.ledger_entry.id} (Subscription: {obj.ledger_entry.subscription})"
        return "No funding source linked"

    funding_source_display.short_description = 'Funding Details'

    def report_content_display(self, obj):
        """Read-only view of the report content JSON"""
        import json
        try:
            return json.dumps(obj.report_content, indent=2)
        except Exception:
            return str(obj.report_content)

    report_content_display.short_description = 'Report Content (JSON)'

    # --- Read-Only Permissions ---
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False