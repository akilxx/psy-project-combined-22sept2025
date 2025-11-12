# testing/tests.py

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
import uuid
from rest_framework.test import APIClient, APITestCase
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from jsonschema import validate as jsonschema_validate, ValidationError as JSONSchemaValidationError
from drf_spectacular.generators import SchemaGenerator
import json
import jsonref
from unittest.mock import patch
from testing.models import PsychometricTest, TestResult
from django.db import OperationalError, connection

User = get_user_model()


class PsychometricTestAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a sample psychometric test with the new structure
        try:
            self.test = PsychometricTest.objects.create(
                test_name='Sample Test',
                options=['Option A', 'Option B', 'Option C'],
                traits=[
                    {"name": "Trait1", "dimensions": ["dim1"]},
                    {"name": "Trait2", "dimensions": ["dim2"]}
                ],
                questions=[
                    {
                        'question number': 1,
                        'scale': 'positive',
                        'trait': 'Trait1',
                        'dimension': 'dim1',
                        'text': 'Question 1 text'
                    },
                    {
                        'question number': 2,
                        'scale': 'negative',
                        'trait': 'Trait2',
                        'dimension': 'dim2',
                        'text': 'Question 2 text'
                    },
                    {
                        'question number': 3,
                        'scale': 'positive',
                        'trait': 'Trait1',
                        'dimension': 'dim1',
                        'text': 'Question 3 text'
                    },
                ]
            )
        except ValidationError as e:
            print('Validation error:', e.message_dict)
            self.fail(f"SetUp failed due to validation error: {e.message_dict}")

        # Create a user
        self.user = User.objects.create_user(email='user@example.com')
        # Generate JWT tokens for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_start_test_anonymous_user(self):
        # Start a new test as an anonymous user
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        if response.status_code != status.HTTP_201_CREATED:
            print("Response status code:", response.status_code)
            print("Response content:", response.json())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('test_result_id', response.json())
        test_result_id = response.json()['test_result_id']
        # Check that test_result_id is stored in session
        session_test_result_ids = self.client.session.get('test_result_ids', [])
        self.assertIn(test_result_id, session_test_result_ids)

    def test_start_test_authenticated_user(self):
        # Start a new test as an authenticated user
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('test_result_id', response.json())
        test_result_id = response.json()['test_result_id']
        # Check that the test result is associated with the user
        test_result = TestResult.objects.get(uuid=test_result_id)
        self.assertEqual(test_result.user, self.user)

    def test_submit_answer_before_completion(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit an answer to question 1
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={'answer': 'Option A'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['detail'], 'Answer submitted.')
        self.assertEqual(response.json()['completed'], False)
        self.assertEqual(response.json()['progress'], '1 / 3')

    def test_manual_completion_of_test(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit answers to all questions
        for q_num in [1, 2, 3]:
            response = self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={q_num}",
                data={'answer': 'Option A'},
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the test is not automatically completed
        test_result = TestResult.objects.get(uuid=test_result_id)
        self.assertFalse(test_result.completed)

        # Manually complete the test
        response = self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={test_result_id}",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['detail'], 'Test marked as completed.')

        # Verify that the test is marked as completed
        test_result.refresh_from_db()
        self.assertTrue(test_result.completed)
        self.assertIsNotNone(test_result.scores)
        self.assertIsNotNone(test_result.percentiles)

    def test_overlapping_submissions_retry_on_sqlite(self):
        # Ensure the regression only runs when using SQLite, which may raise locked errors
        self.assertEqual(connection.vendor, 'sqlite')

        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        original_save = TestResult.save
        save_state = {'called': False}

        def flaky_save(instance, *args, **kwargs):
            if not save_state['called']:
                save_state['called'] = True
                raise OperationalError('database is locked')
            return original_save(instance, *args, **kwargs)

        with patch.object(TestResult, 'save', side_effect=flaky_save):
            response_one = self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
                data={'answer': 'Option A'},
                format='json'
            )

        response_two = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=2",
            data={'answer': 'Option B'},
            format='json'
        )

        self.assertEqual(response_one.status_code, status.HTTP_200_OK)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK)

        stored_result = TestResult.objects.get(uuid=test_result_id)
        self.assertEqual(stored_result.answers['1']['answer'], 'Option A')
        self.assertEqual(stored_result.answers['2']['answer'], 'Option B')

    def test_update_answer_after_completion(self):
        # Start a new test
        response = self.client.post(reverse('testing:test-start'), data={'test': self.test.id}, format='json')
        test_result_id = response.json()['test_result_id']

        # Submit answers to all questions
        for q_num in [1, 2, 3]:
            response = self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={q_num}",
                data={'answer': 'Option A'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manually complete the test
        response = self.client.post(f"{reverse('testing:test-complete')}?test_result_id={test_result_id}", format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Attempt to update an answer after completion
        response = self.client.post(f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
                                    data={'answer': 'Option B'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'Cannot submit answers to a completed test.')

        # Verify that scores and percentiles remain unchanged
        test_result = TestResult.objects.get(uuid=test_result_id)
        self.assertIsNotNone(test_result.scores)
        self.assertIsNotNone(test_result.percentiles)

    def test_set_complete_on_already_completed_test(self):
        # Start a new test and obtain the test_result_id
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit answers for all questions so that the test can be marked as complete.
        for question in self.test.questions:
            question_number = question['question number']
            answer_data = {'answer': 'Option A'}  # Use a valid answer from the test options.
            answer_response = self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={question_number}",
                data=answer_data,
                format='json'
            )
            self.assertEqual(answer_response.status_code, status.HTTP_200_OK)

        # Mark the test as complete for the first time.
        response = self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={test_result_id}",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Attempt to complete the test again.
        response = self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={test_result_id}",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'Test is already marked as completed.')

    def test_overlapping_submissions_preserve_answers(self):
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_result_id = response.json()['test_result_id']

        first_instance = TestResult.objects.get(uuid=test_result_id)
        second_instance = TestResult.objects.get(uuid=test_result_id)

        answer_url_template = f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={{}}"

        with patch('testing.views.TestResultViewSet.get_test_result', side_effect=[first_instance, second_instance]):
            response_first = self.client.post(
                answer_url_template.format(1),
                data={'answer': 'Option A'},
                format='json'
            )
            self.assertEqual(response_first.status_code, status.HTTP_200_OK)

            response_second = self.client.post(
                answer_url_template.format(2),
                data={'answer': 'Option B'},
                format='json'
            )
            self.assertEqual(response_second.status_code, status.HTTP_200_OK)

        test_result = TestResult.objects.get(uuid=test_result_id)
        self.assertIn('1', test_result.answers)
        self.assertIn('2', test_result.answers)
        self.assertEqual(test_result.answers['1']['answer'], 'Option A')
        self.assertEqual(test_result.answers['2']['answer'], 'Option B')

    def test_submit_answer_invalid_question_number(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit an answer with an invalid question number
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=99",
            data={'answer': 'Option A'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Question not found.')

    def test_submit_answer_invalid_answer_option(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit an invalid answer option
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={'answer': 'Invalid Option'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Answer not a valid option.", response.json()['answer'][0])

    def test_access_control_anonymous_user(self):
        # Start a new test as anonymous user
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Clear cookies to simulate loss of session
        self.client.cookies.clear()
        response = self.client.get(
            f"{reverse('testing:test-detail')}?test_result_id={test_result_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Test not found or access denied.')

    def test_access_control_authenticated_user(self):
        # Start a new test as authenticated user
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Try to access the test with a different user
        new_user = User.objects.create_user(email='other@example.com')
        refresh = RefreshToken.for_user(new_user)
        new_access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + new_access_token)

        response = self.client.get(
            f"{reverse('testing:test-detail')}?test_result_id={test_result_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Test not found or access denied.')

    def test_set_complete_invalid_test_result_id(self):
        # Attempt to complete a non-existent test
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        response = self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={invalid_uuid}",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Test not found or access denied.')

    def test_submit_answer_without_question_number(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Attempt to submit an answer without question_number
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}",
            data={'answer': 'Option A'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'question_number is required as a query parameter.')

    def test_submit_answer_without_answer_field(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Attempt to submit an answer without the 'answer' field
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('answer', response.json())

    def test_list_tests_authenticated_user(self):
        # Start and complete a test as an authenticated user
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']
        response = self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={test_result_id}",
            format='json'
        )

        # List all tests
        response = self.client.get(reverse('testing:test-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.json()) >= 1)

    def test_associate_test_with_user(self):
        # Start a new test as an anonymous user
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Authenticate
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)

        # Associate the test with the user
        response = self.client.post(
            f"{reverse('testing:test-associate-user')}?test_result_id={test_result_id}",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['detail'], 'TestResult associated with user.')

        # Verify that the test is associated with the user
        test_result = TestResult.objects.get(uuid=test_result_id)
        self.assertEqual(test_result.user, self.user)

    def test_update_answer_invalid_test_result_id(self):
        # Attempt to submit an answer to a non-existent test
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={invalid_uuid}&question_number=1",
            data={'answer': 'Option A'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Test not found or access denied.')

    def test_start_test_without_test_id(self):
        # Attempt to start a test without providing a test ID
        response = self.client.post(
            reverse('testing:test-start'),
            data={},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('test', response.json())
        self.assertIn('This field is required.', response.json()['test'])

    def test_submit_answer_similar_option(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit an answer that is similar to an option but not exact (case-sensitive)
        similar_answer = 'option a'  # Lowercase version
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={'answer': similar_answer},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('answer', response.json())
        self.assertIn("Answer not a valid option.", response.json()['answer'][0])

    def test_submit_answer_max_length(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit an answer that exceeds maximum length (assuming max_length is less than 1000)
        long_answer = 'A' * 1000
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={'answer': long_answer},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('answer', response.json())
        self.assertIn('Answer not a valid option.', response.json()['answer'][0])

    def test_associate_test_with_different_user(self):
        # Start a new test as an anonymous user
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Authenticate as a different user
        other_user = User.objects.create_user(email='otheruser@example.com')
        refresh = RefreshToken.for_user(other_user)
        other_access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + other_access_token)

        # Attempt to associate the test with the authenticated user
        response = self.client.post(
            f"{reverse('testing:test-associate-user')}?test_result_id={test_result_id}",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the test is associated with the authenticated user
        test_result = TestResult.objects.get(uuid=test_result_id)
        self.assertEqual(test_result.user, other_user)

        # Attempt to associate the same test result with another user (should fail)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        response = self.client.post(
            f"{reverse('testing:test-associate-user')}?test_result_id={test_result_id}",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Test not found in your session.')

    def test_set_complete_without_test_result_id(self):
        # Attempt to complete a test without test_result_id
        response = self.client.post(
            reverse('testing:test-complete'),
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'test_result_id is required as a query parameter.')

    def test_start_test_with_invalid_test_id(self):
        # Attempt to start a test with an invalid test ID
        invalid_test_id = 555  # Assuming this ID does not exist
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': invalid_test_id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('test', response.json())
        self.assertIn('Invalid pk', response.json()['test'][0])

    def test_list_tests_with_completed_filter(self):
        # Authenticate the client
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)

        # --- Start and complete a test ---
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        completed_test_result_id = response.json()['test_result_id']

        # Submit answers for all questions
        for question in self.test.questions:
            question_number = question['question number']
            answer_data = {'answer': 'Option A'}
            answer_response = self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={completed_test_result_id}&question_number={question_number}",
                data=answer_data,
                format='json'
            )
            self.assertEqual(answer_response.status_code, status.HTTP_200_OK)

        # Mark the test as complete
        complete_response = self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={completed_test_result_id}",
            format='json'
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        # --- Start an in-progress test ---
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        in_progress_test_result_id = response.json()['test_result_id']

        # List completed tests
        response = self.client.get(f"{reverse('testing:test-list')}?completed=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_result_ids = [test['uuid'] for test in response.json()]
        self.assertIn(completed_test_result_id, test_result_ids)
        self.assertNotIn(in_progress_test_result_id, test_result_ids)

        # List in-progress tests
        response = self.client.get(f"{reverse('testing:test-list')}?completed=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_result_ids = [test['uuid'] for test in response.json()]
        self.assertNotIn(completed_test_result_id, test_result_ids)
        self.assertIn(in_progress_test_result_id, test_result_ids)

    def test_submit_answer_nonexistent_question_number(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Use a question number that doesn't exist
        nonexistent_question_number = 9999
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={nonexistent_question_number}",
            data={'answer': 'Option A'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Question not found.')

    def test_submit_answer_invalid_question_number_type(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Use a non-integer value for question_number
        invalid_question_number = 'one'
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={invalid_question_number}",
            data={'answer': 'Option A'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'Invalid question_number.')

    def test_submit_answer_with_extra_fields(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit an answer with an extra field; extra fields should be ignored.
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={'answer': 'Option A', 'extra_field': 'Extra Value'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_result = TestResult.objects.get(uuid=test_result_id)
        self.assertNotIn('extra_field', test_result.answers['1'])

    def test_session_persistence(self):
        # Start a new test as anonymous user
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Simulate a new session by clearing cookies
        self.client.cookies.clear()

        # Try to access the test result
        response = self.client.get(
            f"{reverse('testing:test-detail')}?test_result_id={test_result_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Test not found or access denied.')

    def test_retrieve_test_without_test_result_id(self):
        response = self.client.get(reverse('testing:test-detail'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'test_result_id is required as a query parameter.')

    def test_submit_answer_to_completed_test(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit answers for all questions
        for question in self.test.questions:
            question_number = question['question number']
            answer_data = {'answer': 'Option A'}
            answer_response = self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={question_number}",
                data=answer_data,
                format='json'
            )
            self.assertEqual(answer_response.status_code, status.HTTP_200_OK)

        # Mark the test as complete
        complete_response = self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={test_result_id}",
            format='json'
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        # Attempt to submit an answer after completion
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={'answer': 'Option A'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'Cannot submit answers to a completed test.')

    def test_list_tests_with_invalid_completed_parameter(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        response = self.client.get(f"{reverse('testing:test-list')}?completed=invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.json())
        self.assertIn('Invalid value for completed parameter.', response.json()['detail'])

    def test_associate_test_with_invalid_test_result_id(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        response = self.client.post(
            f"{reverse('testing:test-associate-user')}?test_result_id=invalid-uuid",
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'Invalid test_result_id format.')

    def test_submit_answer_with_unicode_characters(self):
        # Start a new test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit an answer with Unicode characters (e.g., Chinese)
        unicode_answer = '选项A'
        response = self.client.post(
            f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number=1",
            data={'answer': unicode_answer},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_full_user_journey_anonymous_user(self):
        # Start a test as an anonymous user
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit answers for all questions
        for q_num in [1, 2, 3]:
            self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={q_num}",
                data={'answer': 'Option A'},
                format='json'
            )

        # Complete the test
        self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={test_result_id}",
            format='json'
        )

        # Retrieve results
        response = self.client.get(f"{reverse('testing:test-detail')}?test_result_id={test_result_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_manipulation_access_denied(self):
        # Start a new test as anonymous user
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        valid_test_result_id = response.json()['test_result_id']

        # Simulate another test result that the user should not have access to
        other_test_result = TestResult.objects.create(test=self.test)
        # Do NOT add this test_result_id to the session

        # Attempt to access the unauthorized test result
        response = self.client.get(
            f"{reverse('testing:test-detail')}?test_result_id={other_test_result.uuid}"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['detail'], 'Test not found or access denied.')

        # Verify that we can still access the valid test result
        response = self.client.get(
            f"{reverse('testing:test-detail')}?test_result_id={valid_test_result_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_full_user_journey_authenticated_user(self):
        # Authenticate as a user
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)

        # Start a test
        response = self.client.post(
            reverse('testing:test-start'),
            data={'test': self.test.id},
            format='json'
        )
        test_result_id = response.json()['test_result_id']

        # Submit answers for all questions
        for q_num in [1, 2, 3]:
            self.client.post(
                f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={q_num}",
                data={'answer': 'Option A'},
                format='json'
            )

        # Complete the test
        self.client.post(
            f"{reverse('testing:test-complete')}?test_result_id={test_result_id}",
            format='json'
        )

        # Retrieve results
        response = self.client.get(f"{reverse('testing:test-detail')}?test_result_id={test_result_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# Schema and OpenAPI validation tests

class SchemaValidationTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)
        schema_json = json.dumps(schema)
        cls.schema_dict = jsonref.loads(schema_json)

    def get_response_schema(self, path, method, status_code):
        paths = self.schema_dict.get('paths', {})
        endpoint = paths.get(path)
        if not endpoint:
            raise KeyError(f"Path '{path}' not found in schema.")

        operation = endpoint.get(method.lower())
        if not operation:
            raise KeyError(f"Method '{method}' for path '{path}' not found in schema.")

        responses = operation.get('responses', {})
        response = responses.get(status_code)
        if not response:
            raise KeyError(f"Response with status code '{status_code}' not found for path '{path}' and method '{method}'.")

        content = response.get('content', {})
        media_type = content.get('application/json')
        if not media_type:
            raise KeyError(f"'application/json' media type not found in responses for path '{path}' and method '{method}'.")

        schema = media_type.get('schema')
        if not schema:
            raise KeyError(f"Schema not found in 'application/json' response for path '{path}' and method '{method}'.")

        return schema

    def validate_response(self, response, schema):
        data = response.json()
        try:
            jsonschema_validate(instance=data, schema=schema)
        except JSONSchemaValidationError as e:
            self.fail(f"Response schema validation failed: {e.message}")


class PsychometricTestBaseTests(SchemaValidationTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test = PsychometricTest.objects.create(
            test_name='Sample Test',
            questions=[
                {'question number': 1, 'scale': 'Scale1', 'trait': 'Trait1', 'dimension': 'dim1', 'text': 'Question 1?'},
                {'question number': 2, 'scale': 'Scale1', 'trait': 'Trait1', 'dimension': 'dim1', 'text': 'Question 2?'},
                {'question number': 3, 'scale': 'Scale2', 'trait': 'Trait2', 'dimension': 'dim2', 'text': 'Question 3?'},
            ],
            options=['Option A', 'Option B', 'Option C'],
            traits=[{"name": "Trait1", "dimensions": ["dim1"]}, {"name": "Trait2", "dimensions": ["dim2"]}],
        )


class TestStartTests(PsychometricTestBaseTests):
    def setUp(self):
        self.client = APIClient()
        self.test_start_url = reverse('testing:test-start')

    def test_start_test_response_schema(self):
        data = {'test': self.test.id}
        response = self.client.post(self.test_start_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        schema = self.get_response_schema('/testing/test/start/', 'post', '201')
        self.validate_response(response, schema)


class TestAnswerTests(PsychometricTestBaseTests):
    def setUp(self):
        self.client = APIClient()
        self.test_start_url = reverse('testing:test-start')
        self.test_answer_url = reverse('testing:test-answer')

    def test_submit_answer_response_schema(self):
        data = {'test': self.test.id}
        response = self.client.post(self.test_start_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_result_id = response.data['test_result_id']
        answer_url = f"{self.test_answer_url}?test_result_id={test_result_id}&question_number=1"
        answer_data = {'answer': 'Option A'}
        response = self.client.post(answer_url, answer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schema = self.get_response_schema('/testing/test/answer/', 'post', '200')
        self.validate_response(response, schema)


class TestCompleteTests(PsychometricTestBaseTests):
    def setUp(self):
        self.client = APIClient()
        self.test_start_url = reverse('testing:test-start')
        self.test_complete_url = reverse('testing:test-complete')
        self.test_answer_url = reverse('testing:test-answer')

    def test_complete_test_response_schema(self):
        data = {'test': self.test.id}
        response = self.client.post(self.test_start_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_result_id = response.data['test_result_id']
        for question in self.test.questions:
            question_number = question['question number']
            answer_data = {'answer': 'Option A'}
            answer_response = self.client.post(
                f"{self.test_answer_url}?test_result_id={test_result_id}&question_number={question_number}",
                data=answer_data,
                format='json'
            )
            self.assertEqual(answer_response.status_code, status.HTTP_200_OK)
        complete_url = f"{self.test_complete_url}?test_result_id={test_result_id}"
        response = self.client.post(complete_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schema = self.get_response_schema('/testing/test/complete/', 'post', '200')
        self.validate_response(response, schema)


class TestDetailTests(PsychometricTestBaseTests):
    def setUp(self):
        self.client = APIClient()
        self.test_start_url = reverse('testing:test-start')
        self.test_detail_url = reverse('testing:test-detail')
        self.test_complete_url = reverse('testing:test-complete')
        self.test_answer_url = reverse('testing:test-answer')

    def test_test_detail_response_schema(self):
        data = {'test': self.test.id}
        response = self.client.post(self.test_start_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_result_id = response.data['test_result_id']
        for question_number in range(1, 4):
            answer_url = f"{self.test_answer_url}?test_result_id={test_result_id}&question_number={question_number}"
            answer_data = {'answer': 'Option A'}
            response = self.client.post(answer_url, answer_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        complete_url = f"{self.test_complete_url}?test_result_id={test_result_id}"
        response = self.client.post(complete_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        detail_url = f"{self.test_detail_url}?test_result_id={test_result_id}"
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schema = self.get_response_schema('/testing/test/', 'get', '200')
        self.validate_response(response, schema)


class TestListTests(PsychometricTestBaseTests):
    def setUp(self):
        self.client = APIClient()
        self.test_start_url = reverse('testing:test-start')
        self.test_list_url = reverse('testing:test-list')

    def test_test_list_response_schema(self):
        data = {'test': self.test.id}
        response = self.client.post(self.test_start_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_result_id = response.data['test_result_id']
        for question_number in range(1, 4):
            answer_url = f"{reverse('testing:test-answer')}?test_result_id={test_result_id}&question_number={question_number}"
            answer_data = {'answer': 'Option A'}
            response = self.client.post(answer_url, answer_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        complete_url = f"{reverse('testing:test-complete')}?test_result_id={test_result_id}"
        response = self.client.post(complete_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(self.test_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schema = self.get_response_schema('/testing/test/list/', 'get', '200')
        self.validate_response(response, schema)


class TestAssociateUserTests(PsychometricTestBaseTests):
    def setUp(self):
        self.client = APIClient()
        self.test_start_url = reverse('testing:test-start')
        self.test_associate_url = reverse('testing:test-associate-user')
        self.user = User.objects.create_user(email='test@example.com')
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_associate_user_response_schema(self):
        data = {'test': self.test.id}
        response = self.client.post(self.test_start_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_result_id = response.data['test_result_id']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
        associate_url = f"{self.test_associate_url}?test_result_id={test_result_id}"
        response = self.client.post(associate_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schema = self.get_response_schema('/testing/test/associate-user/', 'post', '200')
        self.validate_response(response, schema)
