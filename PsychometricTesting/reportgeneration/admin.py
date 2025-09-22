#reportgeneration/admin.py

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from .models import ReportTemplate, ContentBlock


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
