# testing/serializers.py

from rest_framework import serializers
from .models import PsychometricTest, TestResult
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field

User = get_user_model()

#---------------------------------------------Psychometric Test Serializers----------------------------------------------------------------

class QuestionSerializer(serializers.Serializer):
    """
    Serializer for a single question in a psychometric test.
    """
    question_number = serializers.IntegerField(source='question number', help_text='The sequential number of the question.')
    scale = serializers.CharField(help_text='The scale type associated with the question (e.g., positive or negative).')
    trait = serializers.CharField(help_text='The trait that this question is designed to assess.')
    dimension = serializers.CharField(help_text='The specific dimension of the trait assessed by this question.')
    text = serializers.CharField(help_text='The text content of the question.')

class PsychometricTestSerializer(serializers.ModelSerializer):
    """
    Serializer for the psychometric test, including questions, traits, options, and total questions.
    """
    questions = QuestionSerializer(many=True, help_text='A list of questions included in the test.')
    traits = serializers.JSONField(help_text='A list of traits with dimensions that the test measures.')
    total_questions_number = serializers.IntegerField(read_only=True, help_text='The total number of questions in the test.')
    options = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text='A list of possible answer options for the test questions.'
    )

    class Meta:
        model = PsychometricTest
        fields = '__all__'

class AnswerSerializer(serializers.Serializer):
    """
    Serializer for submitting an answer to a test question.
    """
    answer = serializers.CharField(help_text="The user's answer to the question.")

class TestResultSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and retrieving test results.
    """
    completed = serializers.BooleanField(read_only=True, help_text='Indicates whether the test has been completed.')
    in_progress = serializers.BooleanField(read_only=True, help_text='Indicates whether the test is currently in progress.')
    test = serializers.PrimaryKeyRelatedField(
        queryset=PsychometricTest.objects.all(),
        required=True,
        help_text='The psychometric test associated with this result.'
    )

    class Meta:
        model = TestResult
        fields = ['uuid', 'test', 'attempt_number', 'created_at', 'completed', 'in_progress']
        read_only_fields = ['uuid', 'attempt_number', 'created_at', 'completed', 'in_progress']

class AnswerSubmissionSerializer(serializers.Serializer):
    """
    Serializer for submitting or updating an answer to a test question.
    """
    answer = serializers.CharField(help_text="The user's answer to the question, must be one of the valid options.")

    def validate(self, data):
        test_result = self.context.get('test_result')
        question_number = self.context.get('question_number')

        if not test_result or question_number is None:
            raise serializers.ValidationError("TestResult and question_number context are required.")

        answer_text = data['answer']

        # Validate that the answer is in the options provided by the test.
        if answer_text not in test_result.test.options:
            raise serializers.ValidationError({
                'answer': "Answer not a valid option."
            })

        return data

class ScoreSerializer(serializers.Serializer):
    """
    Serializer for computed scores for a trait.
    """
    trait = serializers.CharField(help_text='The trait associated with the score.')
    dimension_scores = serializers.DictField(child=serializers.IntegerField(), help_text='The computed scores for each dimension.')
    total_score = serializers.IntegerField(help_text='The total score for the trait (sum of dimension scores).')

class PercentileSerializer(serializers.Serializer):
    """
    Serializer for computed percentiles for a trait.
    """
    trait = serializers.CharField(help_text='The trait associated with the percentile.')
    dimension_percentiles = serializers.DictField(child=serializers.IntegerField(), help_text='The percentile for each dimension.')
    total_percentile = serializers.IntegerField(help_text='The percentile for the total score of the trait.')

class IndividualAnswerSerializer(serializers.Serializer):
    """
    Serializer for an individual answer in the test results.
    """
    question_number = serializers.IntegerField(help_text='The sequential number of the question.')
    scale = serializers.CharField(help_text='The scale type associated with the question.')
    trait = serializers.CharField(help_text='The trait that this question is designed to assess.')
    dimension = serializers.CharField(help_text='The specific dimension of the trait for this question.')
    text = serializers.CharField(help_text='The text content of the question.')
    answer = serializers.CharField(help_text="The user's answer to the question.")

class TestResultDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed test result information, including answers, scores, and percentiles.
    """
    answers = serializers.SerializerMethodField(help_text="A dictionary of the user's answers to the test questions.")
    completed = serializers.BooleanField(read_only=True, help_text='Indicates whether the test has been completed.')
    in_progress = serializers.BooleanField(read_only=True, help_text='Indicates whether the test is currently in progress.')
    test = PsychometricTestSerializer(help_text='The psychometric test associated with this result.')
    scores = serializers.SerializerMethodField(help_text='The computed scores for the test.')
    percentiles = serializers.SerializerMethodField(help_text='The percentile rankings based on the scores.')

    class Meta:
        model = TestResult
        fields = [
            'uuid', 'test', 'attempt_number', 'created_at',
            'completed', 'in_progress', 'answers', 'scores', 'percentiles'
        ]

    @extend_schema_field(serializers.DictField(child=IndividualAnswerSerializer()))
    def get_answers(self, obj):
        """
        Build the answers mapping from normalized TestAnswer rows.

        Shape:
        {
          "1": {
            "question_number": 1,
            "scale": "...",
            "trait": "...",
            "dimension": "...",
            "text": "...",
            "answer": "..."
          },
          ...
        }
        """
        formatted_answers = {}
        for answer in obj.test_answers.all().order_by('question_number'):
            formatted_answers[str(answer.question_number)] = {
                'question_number': answer.question_number,
                'scale': answer.scale,
                'trait': answer.trait,
                'dimension': answer.dimension,
                'text': answer.text,
                'answer': answer.answer,
            }
        return formatted_answers

    @extend_schema_field(ScoreSerializer(many=True))
    def get_scores(self, obj):
        return obj.scores

    @extend_schema_field(PercentileSerializer(many=True))
    def get_percentiles(self, obj):
        return obj.percentiles

class TestResultCreateResponseSerializer(serializers.Serializer):
    test_result_id = serializers.UUIDField(
        source='uuid',
        help_text="The unique identifier of the created TestResult."
    )

class AnswerSubmissionResponseSerializer(serializers.Serializer):
    """
    Serializer for the response returned after submitting or updating an answer.
    """
    detail = serializers.CharField(
        help_text="A message indicating that the answer was submitted."
    )
    completed = serializers.BooleanField(
        help_text="Indicates whether the test has been completed."
    )
    progress = serializers.CharField(
        help_text="A string representing the user's progress through the test (e.g., '3 / 10')."
    )
    answers = serializers.DictField(
        child=IndividualAnswerSerializer(),
        help_text=(
            "Mapping of question_number (as string) to the updated answer payload, "
            "built from TestAnswer rows."
        ),
    )


class CompletionResponseSerializer(serializers.Serializer):
    """
    Serializer for the response returned after marking a test as completed.
    """
    detail = serializers.CharField(help_text="A message indicating that the test was marked as completed.")

class AssociationResponseSerializer(serializers.Serializer):
    """
    Serializer for the response returned after associating a test with a user account.
    """
    detail = serializers.CharField(help_text="A message indicating that the TestResult was associated with the user.")

class TestResultListSerializer(serializers.ModelSerializer):
    """
    Serializer for test result listings.
    """
    scores = serializers.SerializerMethodField(help_text='The computed scores for the test.')
    percentiles = serializers.SerializerMethodField(help_text='The percentile rankings based on the scores.')
    test = serializers.PrimaryKeyRelatedField(
        queryset=PsychometricTest.objects.all(),
        help_text='The psychometric test associated with this result.'
    )
    test_name = serializers.CharField(source='test.test_name', read_only=True, help_text='The name of the test.')
    has_report = serializers.SerializerMethodField(help_text='Whether a report exists for this test result.')

    class Meta:
        model = TestResult
        fields = ['uuid', 'test', 'test_name', 'attempt_number', 'created_at', 'completed', 'in_progress', 'scores', 'percentiles', 'has_report']

    @extend_schema_field(ScoreSerializer(many=True, allow_null=True))
    def get_scores(self, obj):
        return obj.scores

    @extend_schema_field(PercentileSerializer(many=True, allow_null=True))
    def get_percentiles(self, obj):
        return obj.percentiles

    def get_has_report(self, obj):
        """Check if a TestReport exists for this TestResult."""
        return hasattr(obj, 'generated_report') and obj.generated_report is not None

class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer for error responses.
    """
    detail = serializers.CharField(help_text="A message describing the error.")
