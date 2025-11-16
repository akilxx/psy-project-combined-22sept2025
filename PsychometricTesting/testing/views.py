# testing/views.py

import logging
import uuid

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from django.db import transaction, connection
from django.db.models import F, Func, JSONField, Value
from django.db.models.functions import Coalesce

from .serializers import (
    TestResultSerializer,
    TestResultDetailSerializer,
    AnswerSubmissionSerializer,
    TestResultCreateResponseSerializer,
    AnswerSubmissionResponseSerializer,
    CompletionResponseSerializer,
    AssociationResponseSerializer,
    TestResultListSerializer,
    ErrorResponseSerializer,
)
from .models import TestResult


class JSONSetAnswer(Func):
    """Database-agnostic helper to upsert a single key in a JSON column."""

    def __init__(self, expression, question_number, payload, **extra):
        key = str(question_number)
        json_value = Value(payload, output_field=JSONField())
        vendor = connection.vendor

        if vendor == 'postgresql':
            path = Value(f'{{{key}}}')
            expressions = (
                Coalesce(expression, Value({}, output_field=JSONField())),
                path,
                json_value,
                Value(True),
            )
            extra.setdefault('function', 'jsonb_set')
        elif vendor == 'sqlite':
            path = Value(f'$."{key}"')
            expressions = (
                Coalesce(expression, Value({}, output_field=JSONField())),
                path,
                json_value,
            )
            extra.setdefault('function', 'json_set')
        else:
            raise NotImplementedError(
                f"Unsupported database vendor '{vendor}' for JSON answer updates."
            )

        extra.setdefault('output_field', JSONField())
        super().__init__(*expressions, **extra)

User = get_user_model()
logger = logging.getLogger(__name__)


class TestResultViewSet(viewsets.ViewSet):
    """
    A viewset for managing test results, including starting a test, submitting answers,
    marking tests as complete, and associating anonymous tests with a user.
    """
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        request=TestResultSerializer,
        responses={
            201: TestResultCreateResponseSerializer,
            400: ErrorResponseSerializer,
        },
        description="Start a new psychometric test.",
        examples=[
            OpenApiExample(
                'Successful Response',
                value={"test_result_id": "123e4567-e89b-12d3-a456-426614174000"},
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                'Error Response',
                value={"test": ["This field is required."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def create(self, request):
        """
        Create a new TestResult for a psychometric test.
        Authenticated users get their TestResult associated with their account;
        anonymous users have the test stored in session.
        """
        serializer = TestResultSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error("Serializer errors: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        test = serializer.validated_data['test']
        if request.user.is_authenticated:
            test_result = TestResult.objects.create(
                test=test,
                user=request.user,
                session_key=request.session.session_key
            )
        else:
            test_result = TestResult.objects.create(
                test=test,
                session_key=request.session.session_key
            )
            if 'test_result_ids' not in request.session:
                request.session['test_result_ids'] = []
            request.session['test_result_ids'].append(str(test_result.uuid))
            request.session.modified = True

        return Response({'test_result_id': str(test_result.uuid)}, status=status.HTTP_201_CREATED)

    def get_test_result(self, request):
        """
        Helper method to retrieve the TestResult based on the test_result_id query parameter.
        For authenticated users, it ensures the TestResult is associated with their account.
        For anonymous users, it checks the session.
        """
        test_result_id = request.query_params.get('test_result_id')
        if not test_result_id:
            return None
        try:
            test_result_uuid = uuid.UUID(test_result_id)
        except ValueError:
            return None

        if request.user.is_authenticated:
            try:
                test_result = TestResult.objects.get(uuid=test_result_uuid, user=request.user)
                return test_result
            except TestResult.DoesNotExist:
                return None
        else:
            test_result_ids = request.session.get('test_result_ids', [])
            if str(test_result_uuid) not in test_result_ids:
                return None
            try:
                test_result = TestResult.objects.get(uuid=test_result_uuid)
                return test_result
            except TestResult.DoesNotExist:
                return None

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='test_result_id',
                description='UUID of the TestResult to retrieve.',
                required=True,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: TestResultDetailSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        description="Retrieve detailed information about a TestResult, including answers, scores, and percentiles.",
    )
    def retrieve(self, request, pk=None):
        """
        Retrieve details of a specific TestResult.
        """
        test_result_id = request.query_params.get('test_result_id')
        if not test_result_id:
            return Response(
                {'detail': 'test_result_id is required as a query parameter.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            uuid.UUID(test_result_id)
        except ValueError:
            return Response({'detail': 'Invalid test_result_id format.'}, status=status.HTTP_400_BAD_REQUEST)

        test_result = self.get_test_result(request)
        if not test_result:
            return Response({'detail': 'Test not found or access denied.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TestResultDetailSerializer(test_result)
        return Response(serializer.data)

    @extend_schema(
        request=AnswerSubmissionSerializer,
        parameters=[
            OpenApiParameter(
                name='test_result_id',
                description='UUID of the TestResult for which an answer is being submitted or updated.',
                required=True,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name='question_number',
                description='The sequential number of the question being answered.',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: AnswerSubmissionResponseSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        description="Submit or update an answer for a specific question within a TestResult.",
    )
    def submit_or_update_answer(self, request):
        """
        Submit or update an answer for a specific question in a TestResult.
        The submitted answer must be one of the valid options defined in the test.
        """
        test_result = self.get_test_result(request)
        if not test_result:
            return Response({'detail': 'Test not found or access denied.'}, status=status.HTTP_404_NOT_FOUND)

        if test_result.completed:
            return Response({'detail': 'Cannot submit answers to a completed test.'}, status=status.HTTP_400_BAD_REQUEST)

        question_number = request.query_params.get('question_number')
        if not question_number:
            return Response({'detail': 'question_number is required as a query parameter.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            question_number = int(question_number)
        except ValueError:
            return Response({'detail': 'Invalid question_number.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AnswerSubmissionSerializer(
            data=request.data,
            context={'test_result': test_result, 'question_number': question_number}
        )
        serializer.is_valid(raise_exception=True)
        answer_text = serializer.validated_data['answer']

        # Retrieve the question from the test data using the question number.
        question = next(
            (q for q in test_result.test.questions if q['question number'] == question_number),
            None
        )
        if not question:
            return Response({'detail': 'Question not found.'}, status=status.HTTP_404_NOT_FOUND)

        answer_payload = {
            'question number': question_number,
            'scale': question['scale'],
            'trait': question['trait'],
            'dimension': question['dimension'],
            'text': question['text'],
            'answer': answer_text
        }

        with transaction.atomic():
            locked_result = TestResult.objects.select_for_update().get(pk=test_result.pk)
            TestResult.objects.filter(pk=locked_result.pk).update(
                answers=JSONSetAnswer(F('answers'), question_number, answer_payload)
            )
            locked_result.refresh_from_db(fields=['answers'])

        progress = f"{len(locked_result.answers)} / {test_result.test.total_questions_number}"
        return Response({
            'detail': 'Answer submitted.',
            'completed': locked_result.completed,
            'progress': progress,
            'answers': locked_result.answers
        }, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        parameters=[
            OpenApiParameter(
                name='test_result_id',
                description='UUID of the TestResult to mark as complete.',
                required=True,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: CompletionResponseSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        description="Mark a TestResult as completed manually once all questions have been answered.",
    )
    def set_complete(self, request):
        """
        Manually mark a TestResult as complete.
        """
        test_result_id = request.query_params.get('test_result_id')
        if not test_result_id:
            return Response(
                {'detail': 'test_result_id is required as a query parameter.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            uuid.UUID(test_result_id)
        except ValueError:
            return Response({'detail': 'Invalid test_result_id format.'}, status=status.HTTP_400_BAD_REQUEST)

        test_result = self.get_test_result(request)
        if not test_result:
            return Response({'detail': 'Test not found or access denied.'}, status=status.HTTP_404_NOT_FOUND)

        if test_result.completed:
            return Response({'detail': 'Test is already marked as completed.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(test_result.answers) == test_result.test.total_questions_number:
            test_result.completed = True
            test_result.save()
            return Response({'detail': 'Test marked as completed.'}, status=status.HTTP_200_OK)

        return Response({'detail': 'Test could not be marked as completed.'}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=None,
        parameters=[
            OpenApiParameter(
                name='test_result_id',
                description='UUID of the TestResult to associate with the authenticated user.',
                required=True,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: AssociationResponseSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        description="Associate an anonymous TestResult with the currently authenticated user.",
    )
    def associate_user(self, request):
        """
        Associate an anonymous TestResult with the authenticated user.
        """
        test_result_id = request.query_params.get('test_result_id')
        if not test_result_id:
            return Response({'detail': 'test_result_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            test_result_uuid = uuid.UUID(test_result_id)
        except ValueError:
            return Response({'detail': 'Invalid test_result_id format.'}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.is_authenticated:
            return Response({'detail': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)

        test_result_ids = request.session.get('test_result_ids', [])
        if str(test_result_uuid) not in test_result_ids:
            return Response({'detail': 'Test not found in your session.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            test_result = TestResult.objects.get(uuid=test_result_uuid)
        except TestResult.DoesNotExist:
            return Response({'detail': 'Test not found.'}, status=status.HTTP_404_NOT_FOUND)

        if test_result.user is not None:
            return Response({'detail': 'Test already associated with a user.'}, status=status.HTTP_400_BAD_REQUEST)

        test_result.user = request.user
        test_result.save()

        test_result_ids.remove(test_result_id)
        request.session['test_result_ids'] = test_result_ids
        request.session.modified = True

        return Response({'detail': 'TestResult associated with user.'}, status=status.HTTP_200_OK)


class TestResultListView(generics.GenericAPIView):
    """
    API view for listing TestResults for the authenticated user or from session for anonymous users.
    """
    serializer_class = TestResultListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        responses=TestResultListSerializer(many=True),
        parameters=[
            OpenApiParameter(
                name='completed',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter tests by completion status ('true' or 'false').",
                required=False,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve a list of TestResult instances.
        For authenticated users, optionally filter by completion status.
        For anonymous users, only TestResults stored in the session are returned.
        """
        if request.user.is_authenticated:
            completed_param = request.query_params.get('completed')
            if completed_param is not None:
                if completed_param.lower() == 'true':
                    completed = True
                elif completed_param.lower() == 'false':
                    completed = False
                else:
                    return Response(
                        {'detail': 'Invalid value for completed parameter.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                test_results = TestResult.objects.filter(user=request.user, completed=completed)
            else:
                test_results = TestResult.objects.filter(user=request.user)
        else:
            test_result_ids = request.session.get('test_result_ids', [])
            test_results = TestResult.objects.filter(uuid__in=test_result_ids)

        serializer = self.get_serializer(test_results, many=True)
        return Response(serializer.data)
