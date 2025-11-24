# testing/models.py

from django.db import models
from django.core.exceptions import ValidationError
import random
import logging
import uuid
from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from percentile.utils import compute_percentile



# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

User = get_user_model()


def lowercase_keys(data):
    if isinstance(data, dict):
        return {k.lower(): lowercase_keys(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [lowercase_keys(item) for item in data]
    else:
        return data


class PsychometricTest(models.Model):
    test_name = models.CharField(max_length=255)
    options = models.JSONField()  # Must be provided by the user
    questions = models.JSONField()  # Must be provided; each question must include a "dimension"
    traits = models.JSONField()
    # Expected structure for traits:
    # [
    #   {"name": "neuroticism", "dimensions": ["anxiety", "anger", "depression"]},
    #   {"name": "extraversion", "dimensions": ["sociability", "assertiveness"]}
    # ]
    total_questions_number = models.IntegerField(editable=False)  # Calculated field

    def __str__(self):
        return f"Test: {self.test_name} (ID: {self.id})"

    def clean(self):
        super().clean()

        # Validate questions: must be a non-empty list.
        if not isinstance(self.questions, list) or not self.questions:
            raise ValidationError({'questions': 'Questions must be a non-empty list.'})

        # Validate traits: must be a non-empty list of dicts with "name" and "dimensions"
        if not isinstance(self.traits, list) or not self.traits:
            raise ValidationError({'traits': 'Traits must be a non-empty list.'})
        traits_dict = {}
        for trait in self.traits:
            if not isinstance(trait, dict) or 'name' not in trait or 'dimensions' not in trait:
                raise ValidationError({'traits': 'Each trait must be a dict with "name" and "dimensions".'})
            if not isinstance(trait['name'], str):
                raise ValidationError({'traits': 'Trait name must be a string.'})
            if (not isinstance(trait['dimensions'], list) or not trait['dimensions'] or
                    not all(isinstance(d, str) for d in trait['dimensions'])):
                raise ValidationError({'traits': 'Trait dimensions must be a non-empty list of strings.'})
            traits_dict[trait['name'].lower()] = [d.lower() for d in trait['dimensions']]

        # Convert question keys to lowercase.
        self.questions = lowercase_keys(self.questions)

        # Validate each question.
        required_keys = {'question number', 'scale', 'trait', 'dimension', 'text'}
        question_numbers = []
        # Track which trait/dimension combinations are used.
        used_traits_dimensions = {}
        for i, question in enumerate(self.questions):
            if not isinstance(question, dict):
                raise ValidationError({'questions': f'Question at index {i} must be a dictionary.'})
            missing_keys = required_keys - question.keys()
            if missing_keys:
                raise ValidationError({'questions': f'Question at index {i} is missing keys: {missing_keys}'})
            # Ensure unique question numbers.
            question_number = question['question number']
            if question_number in question_numbers:
                raise ValidationError({'questions': 'Question numbers must be unique in the questions list.'})
            question_numbers.append(question_number)

            # Validate that the question's trait and dimension exist in the traits list.
            question_trait = question.get('trait')
            question_dimension = question.get('dimension')
            if not question_trait or not question_dimension:
                raise ValidationError({'questions': f'Question at index {i} must have both "trait" and "dimension".'})
            question_trait_lower = question_trait.lower()
            question_dimension_lower = question_dimension.lower()
            if question_trait_lower not in traits_dict:
                raise ValidationError({
                                          'questions': f'Trait "{question_trait}" in question at index {i} is not defined in the traits list.'})
            if question_dimension_lower not in traits_dict[question_trait_lower]:
                raise ValidationError({
                                          'questions': f'Dimension "{question_dimension}" in question at index {i} is not valid for trait "{question_trait}".'})

            # Record that this trait/dimension is used.
            if question_trait_lower not in used_traits_dimensions:
                used_traits_dimensions[question_trait_lower] = set()
            used_traits_dimensions[question_trait_lower].add(question_dimension_lower)

        # Ensure every trait in traits list appears in at least one question,
        # and every dimension for each trait is used in at least one question.
        for trait_name in traits_dict.keys():
            if trait_name not in used_traits_dimensions:
                raise ValidationError({'traits': f'Trait "{trait_name}" is not used in any question.'})
            for dimension in traits_dict[trait_name]:
                if dimension not in used_traits_dimensions.get(trait_name, set()):
                    raise ValidationError(
                        {'traits': f'Dimension "{dimension}" for trait "{trait_name}" is not used in any question.'})

        # Validate options.
        if not isinstance(self.options, list) or not self.options:
            raise ValidationError({'options': 'Options must be a non-empty list.'})
        for option in self.options:
            if not isinstance(option, str):
                raise ValidationError({'options': 'Each option must be a string.'})

    def save(self, *args, **kwargs):
        # Set total_questions_number based on the length of questions.
        self.total_questions_number = len(self.questions)
        self.full_clean()
        super(PsychometricTest, self).save(*args, **kwargs)


class TestResult(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT, null=True, blank=True)
    test = models.ForeignKey('PsychometricTest', on_delete=models.PROTECT)
    attempt_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    completed = models.BooleanField(default=False)
    in_progress = models.BooleanField(default=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)

    # No more answers JSONField here – answers are normalized in TestAnswer
    scores = models.JSONField(blank=True, null=True)
    percentiles = models.JSONField(blank=True, null=True)

    def __str__(self):
        user_id = self.user.email if self.user else 'Anonymous'
        return (
            f"TestResult(id={self.uuid}, user_id={user_id}, "
            f"test={self.test.test_name}, Date={self.created_at})"
        )

    def delete(self, *args, **kwargs):
        """
        Prevent deletion of TestResult instances.
        This is the only hard business rule enforced at the model level.
        """
        raise ProtectedError("Deletion of TestResult instances is not allowed.", self)

    # ---------- Row-based helpers (no side effects) ----------

    def get_answer_rows(self):
        """
        Convenience helper to fetch all TestAnswer rows for this result.
        Uses the `test_answers` related_name on TestAnswer.test_result.
        """
        return list(self.test_answers.all())

    def get_unanswered_questions(self):
        """
        Return question dicts from self.test.questions that do NOT yet
        have a corresponding TestAnswer row.
        """
        answered_numbers = {a.question_number for a in self.get_answer_rows()}
        return [
            q for q in self.test.questions
            if q['question number'] not in answered_numbers
        ]

    def _compute_scores_from_rows(self, answer_rows):
        """
        Compute scores per trait and per dimension from normalized TestAnswer rows.

        Returns:
            list of:
            [
              {
                "trait": "<trait-name>",
                "dimension_scores": {"dim1": <score>, ...},
                "total_score": <sum of dimensions>,
              },
              ...
            ]
        """
        options = self.test.options
        num_options = len(options)
        positive_scale = {option: idx + 1 for idx, option in enumerate(options)}
        negative_scale = {option: num_options - idx for idx, option in enumerate(options)}

        # Initialise scores structure per trait/dimension
        scores = {}
        for trait in self.test.traits:
            trait_name = trait['name'].lower()
            scores[trait_name] = {
                'dimension_scores': {d.lower(): 0 for d in trait['dimensions']},
                'total_score': 0,
            }

        # Aggregate over normalized answers (TestAnswer rows)
        for answer_obj in answer_rows:
            answer_text = answer_obj.answer
            scale_type = answer_obj.scale
            trait = answer_obj.trait
            dimension = answer_obj.dimension

            if not (answer_text and scale_type and trait and dimension):
                continue

            scale_type_lower = scale_type.lower()
            if scale_type_lower == 'positive':
                score_value = positive_scale.get(answer_text)
            elif scale_type_lower == 'negative':
                score_value = negative_scale.get(answer_text)
            else:
                continue

            if score_value is None:
                continue

            trait_key = trait.lower()
            dimension_key = dimension.lower()
            trait_entry = scores.get(trait_key)
            if not trait_entry:
                # Ignore answers for unknown traits
                continue
            if dimension_key not in trait_entry['dimension_scores']:
                # Ignore answers for unknown dimensions
                continue

            trait_entry['dimension_scores'][dimension_key] += score_value

        # Build final list
        result = []
        for trait_key, data in scores.items():
            data['total_score'] = sum(data['dimension_scores'].values())
            result.append({
                'trait': trait_key,
                'dimension_scores': data['dimension_scores'],
                'total_score': data['total_score'],
            })

        return result

    def _compute_percentiles_from_scores(self, scores):
        """
        Compute percentiles per trait and per dimension from the scores structure.

        Returns:
            list of:
            [
              {
                "trait": "<trait-name>",
                "dimension_percentiles": {"dim1": <pct>, ...},
                "total_percentile": <pct>,
              },
              ...
            ]
        """
        if not scores:
            return []

        percentiles = []
        for trait_data in scores:
            dim_percentiles = {
                dim: compute_percentile(dim, score)
                for dim, score in trait_data["dimension_scores"].items()
            }

            total_percentile = compute_percentile(
                trait_data["trait"], trait_data["total_score"]
            )

            percentiles.append({
                "trait": trait_data["trait"],
                "dimension_percentiles": dim_percentiles,
                "total_percentile": total_percentile,
            })

        return percentiles


class TestAnswer(models.Model):
    """
    Normalized answer for a single question in a TestResult.
    One row per (test_result, question_number).
    """
    test_result = models.ForeignKey(
        'TestResult',
        on_delete=models.CASCADE,
        related_name='test_answers',
    )
    question_number = models.IntegerField()

    # Denormalized metadata from PsychometricTest.questions at the time of answering
    scale = models.CharField(max_length=32)
    trait = models.CharField(max_length=128)
    dimension = models.CharField(max_length=128)
    text = models.TextField()

    # The selected option (must be one of test.options at write time)
    answer = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['test_result', 'question_number'],
                name='uniq_answer_per_result_and_question',
            )
        ]
        indexes = [
            models.Index(fields=['test_result', 'question_number']),
        ]
        ordering = ['question_number']

    def __str__(self):
        return (
            f"Answer(test_result={self.test_result.uuid}, "
            f"q={self.question_number}, answer={self.answer})"
        )
