# testing/admin.py

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import PsychometricTest, TestResult, TestAnswer, lowercase_keys


class PsychometricTestAdmin(admin.ModelAdmin):
    readonly_fields = ('total_questions_number',)
    fields = ('test_name', 'options', 'questions', 'traits', 'total_questions_number')

    def has_change_permission(self, request, obj=None):
        # Prevent changes via the admin interface.
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion via the admin interface.
        return False

    def save_model(self, request, obj, form, change):
        try:
            # Validate options.
            if not obj.options or not isinstance(obj.options, list):
                raise ValidationError("Options must be provided as a non-empty list.")
            for option in obj.options:
                if not isinstance(option, str):
                    raise ValidationError("Each option must be a string.")

            # Validate traits.
            # Now, traits must be a list of dictionaries with keys "name" and "dimensions".
            if not obj.traits or not isinstance(obj.traits, list):
                raise ValidationError("Traits must be provided as a non-empty list.")
            traits_lookup = {}
            for trait in obj.traits:
                if not isinstance(trait, dict):
                    raise ValidationError("Each trait must be a dictionary with keys 'name' and 'dimensions'.")
                if 'name' not in trait or 'dimensions' not in trait:
                    raise ValidationError("Each trait must have 'name' and 'dimensions' keys.")
                if not isinstance(trait['name'], str):
                    raise ValidationError("Trait name must be a string.")
                if (not isinstance(trait['dimensions'], list) or not trait['dimensions'] or
                        not all(isinstance(dim, str) for dim in trait['dimensions'])):
                    raise ValidationError("Trait dimensions must be a non-empty list of strings.")
                traits_lookup[trait['name'].lower()] = [dim.lower() for dim in trait['dimensions']]

            # Validate questions.
            # Each question must include: 'question number', 'scale', 'trait', 'dimension', and 'text'.
            if not obj.questions or not isinstance(obj.questions, list):
                raise ValidationError("Questions must be provided as a non-empty list.")
            required_keys = {'question number', 'scale', 'trait', 'dimension', 'text'}
            question_numbers = []
            used_traits_dimensions = {}
            for i, question in enumerate(obj.questions):
                if not isinstance(question, dict):
                    raise ValidationError(f"Question at index {i} must be a dictionary.")
                missing_keys = required_keys - set(question.keys())
                if missing_keys:
                    raise ValidationError(f"Question at index {i} is missing keys: {', '.join(missing_keys)}")

                # Ensure question numbers are unique.
                q_number = question.get('question number')
                if q_number in question_numbers:
                    raise ValidationError("Question numbers must be unique in the questions list.")
                question_numbers.append(q_number)

                # Validate that the question's trait and dimension exist in the traits definition.
                trait = question.get('trait')
                dimension = question.get('dimension')
                if not trait or not dimension:
                    raise ValidationError(f"Question at index {i} must have both 'trait' and 'dimension'.")
                trait_lower = trait.lower()
                dimension_lower = dimension.lower()
                if trait_lower not in traits_lookup:
                    raise ValidationError(f"Trait '{trait}' in question at index {i} is not defined in traits.")
                if dimension_lower not in traits_lookup[trait_lower]:
                    raise ValidationError(
                        f"Dimension '{dimension}' in question at index {i} is not valid for trait '{trait}'.")

                # Record the usage of this trait/dimension.
                if trait_lower not in used_traits_dimensions:
                    used_traits_dimensions[trait_lower] = set()
                used_traits_dimensions[trait_lower].add(dimension_lower)

            # Ensure every trait and every dimension from the traits list appears in at least one question.
            for trait, dims in traits_lookup.items():
                if trait not in used_traits_dimensions:
                    raise ValidationError(f"Trait '{trait}' is not used in any question.")
                for dim in dims:
                    if dim not in used_traits_dimensions.get(trait, set()):
                        raise ValidationError(f"Dimension '{dim}' for trait '{trait}' is not used in any question.")

            # Convert the questions' keys to lowercase.
            obj.questions = lowercase_keys(obj.questions)

            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(request, f"Error: {e}", level=messages.ERROR)


class TestResultReadOnlyAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'attempt_number', 'created_at')
    readonly_fields = ('user', 'test', 'attempt_number', 'scores', 'percentiles', 'created_at')
    fields = ('user', 'test', 'attempt_number', 'scores', 'percentiles', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'test')


class TestAnswerAdmin(admin.ModelAdmin):
    list_display = (
        'test_result', 'question_number', 'selected_option',
        'question_trait', 'question_dimension'
    )
    readonly_fields = (
        'test_result', 'question_number', 'question_scale',
        'question_trait', 'question_dimension', 'question_text',
        'selected_option', 'created_at', 'updated_at'
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(PsychometricTest, PsychometricTestAdmin)
admin.site.register(TestResult, TestResultReadOnlyAdmin)
admin.site.register(TestAnswer, TestAnswerAdmin)
