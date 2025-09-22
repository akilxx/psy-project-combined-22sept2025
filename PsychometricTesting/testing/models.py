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
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    test = models.ForeignKey(PsychometricTest, on_delete=models.PROTECT)
    attempt_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    completed = models.BooleanField(default=False)
    in_progress = models.BooleanField(default=True)  # Indicates if the test is in progress
    session_key = models.CharField(max_length=40, null=True, blank=True)

    scores = models.JSONField(blank=True, null=True)
    # Expected structure:
    # [
    #   {
    #     "trait": "neuroticism",
    #     "dimension_scores": {"anxiety": 12, "anger": 8, "depression": 10},
    #     "total_score": 30
    #   },
    #   ...
    # ]
    percentiles = models.JSONField(blank=True, null=True)
    # Expected structure:
    # [
    #   {
    #     "trait": "neuroticism",
    #     "dimension_percentiles": {"anxiety": 70, "anger": 80, "depression": 65},
    #     "total_percentile": 75
    #   },
    #   ...
    # ]
    answers = models.JSONField(default=dict)  # Dictionary of answers keyed by question number

    def __str__(self):
        user_id = self.user.email if self.user else 'Anonymous'
        return f"TestResult(id={self.uuid}, user_id={user_id}, test={self.test.test_name}, Date={self.created_at})"

    def delete(self, *args, **kwargs):
        raise ProtectedError("Deletion of TestResult instances is not allowed.", self)

    def save(self, *args, **kwargs):
        if self.is_completed():
            self.compute_scores()
            self.compute_percentiles()

        if self.completed:
            self.in_progress = False
        super(TestResult, self).save(*args, **kwargs)

    def get_unanswered_questions(self):
        answered_question_numbers = set(map(int, self.answers.keys()))
        all_question_numbers = set(q['question number'] for q in self.test.questions)
        unanswered_numbers = all_question_numbers - answered_question_numbers
        return [q for q in self.test.questions if q['question number'] in unanswered_numbers]

    def is_completed(self):
        return len(self.answers) == self.test.total_questions_number

    def compute_scores(self):
        """
        Compute scores per trait and per dimension.
        Each answer's score is determined by the test options and scale (positive/negative).
        This method aggregates scores per dimension and calculates a total score per trait.
        """
        options = self.test.options
        num_options = len(options)
        positive_scale = {option: idx + 1 for idx, option in enumerate(options)}
        negative_scale = {option: num_options - idx for idx, option in enumerate(options)}

        scores = {}
        for trait in self.test.traits:
            trait_name = trait['name'].lower()
            scores[trait_name] = {
                'dimension_scores': {d.lower(): 0 for d in trait['dimensions']},
                'total_score': 0
            }

        for answer_data in self.answers.values():
            answer_text = answer_data.get('answer')
            scale_type = answer_data.get('scale')
            trait = answer_data.get('trait')
            dimension = answer_data.get('dimension')
            if not (answer_text and scale_type and trait and dimension):
                continue

            if scale_type.lower() == 'positive':
                score_value = positive_scale.get(answer_text)
            elif scale_type.lower() == 'negative':
                score_value = negative_scale.get(answer_text)
            else:
                continue

            if score_value is None:
                continue

            trait_key = trait.lower()
            dimension_key = dimension.lower()
            if trait_key in scores and dimension_key in scores[trait_key]['dimension_scores']:
                scores[trait_key]['dimension_scores'][dimension_key] += score_value

        # Calculate total score per trait.
        for trait_key, data in scores.items():
            total = sum(data['dimension_scores'].values())
            data['total_score'] = total

        self.scores = [
            {'trait': trait, 'dimension_scores': data['dimension_scores'], 'total_score': data['total_score']}
            for trait, data in scores.items()
        ]

    def compute_percentiles(self):
        """
        Compute percentile scores for each trait and each dimension
        using the local percentile app (no external HTTP requests).
        """
        if not self.scores:
            self.percentiles = []
            return

        percentiles = []
        for trait_data in self.scores:
            # dimensions
            dim_percentiles = {
                dim: compute_percentile(dim, score)
                for dim, score in trait_data["dimension_scores"].items()
            }

            # total for the trait
            total_percentile = compute_percentile(
                trait_data["trait"], trait_data["total_score"]
            )

            percentiles.append({
                "trait": trait_data["trait"],
                "dimension_percentiles": dim_percentiles,
                "total_percentile": total_percentile,
            })

        self.percentiles = percentiles
