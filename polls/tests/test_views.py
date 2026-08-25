from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from polls.models import Choice

from .test_models import create_question


class NoExternalCallsMixin:
    """Stub out the artificial latency the views add for tracing demo purposes.

    ``IndexView`` calls an external HTTP endpoint and ``vote()`` sleeps for a
    second, both only to make the generated traces more interesting. Neither
    belongs in a test run.
    """

    def setUp(self):
        super().setUp()
        requests_get = patch("polls.views.requests.get")
        self.mock_requests_get = requests_get.start()
        self.addCleanup(requests_get.stop)

        sleep = patch("polls.views.time.sleep")
        self.mock_sleep = sleep.start()
        self.addCleanup(sleep.stop)


class IndexViewTests(NoExternalCallsMixin, TestCase):
    def test_no_questions(self):
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_question_is_listed(self):
        question = create_question("What is new?", days=-1)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "What is new?")
        self.assertQuerySetEqual(response.context["latest_question_list"], [question])

    def test_questions_are_ordered_by_pub_date_descending(self):
        older = create_question("Older question.", days=-30)
        newer = create_question("Newer question.", days=-1)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(response.context["latest_question_list"], [newer, older])

    def test_at_most_five_questions_are_listed(self):
        for i in range(6):
            create_question(f"Question {i}", days=-i - 1)
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(len(response.context["latest_question_list"]), 5)

    def test_external_request_is_issued(self):
        """The demo view calls an external endpoint so the trace has a child span."""
        self.client.get(reverse("polls:index"))
        self.mock_requests_get.assert_called_once()


class DetailViewTests(NoExternalCallsMixin, TestCase):
    def test_question_is_rendered_with_its_choices(self):
        question = create_question("What is new?", days=-1)
        Choice.objects.create(question=question, choice_text="Not much")
        response = self.client.get(reverse("polls:detail", args=(question.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is new?")
        self.assertContains(response, "Not much")

    def test_unknown_question_returns_404(self):
        response = self.client.get(reverse("polls:detail", args=(1234,)))
        self.assertEqual(response.status_code, 404)


class ResultsViewTests(NoExternalCallsMixin, TestCase):
    def test_votes_are_rendered(self):
        question = create_question("What is new?", days=-1)
        Choice.objects.create(question=question, choice_text="Not much", votes=3)
        response = self.client.get(reverse("polls:results", args=(question.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not much -- 3 votes")

    def test_unknown_question_returns_404(self):
        response = self.client.get(reverse("polls:results", args=(1234,)))
        self.assertEqual(response.status_code, 404)


class VoteViewTests(NoExternalCallsMixin, TestCase):
    def test_vote_increments_the_selected_choice(self):
        question = create_question("What is new?", days=-1)
        choice = Choice.objects.create(question=question, choice_text="Not much")
        other = Choice.objects.create(question=question, choice_text="The sky")

        response = self.client.post(
            reverse("polls:vote", args=(question.id,)), {"choice": choice.id}
        )

        self.assertRedirects(response, reverse("polls:results", args=(question.id,)))
        choice.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(choice.votes, 1)
        self.assertEqual(other.votes, 0)

    def test_vote_without_a_choice_redisplays_the_form(self):
        question = create_question("What is new?", days=-1)
        Choice.objects.create(question=question, choice_text="Not much")

        response = self.client.post(reverse("polls:vote", args=(question.id,)), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You didn&#x27;t select a choice.")

    def test_vote_for_an_unknown_choice_redisplays_the_form(self):
        question = create_question("What is new?", days=-1)

        response = self.client.post(reverse("polls:vote", args=(question.id,)), {"choice": 1234})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You didn&#x27;t select a choice.")

    def test_vote_for_an_unknown_question_returns_404(self):
        response = self.client.post(reverse("polls:vote", args=(1234,)), {"choice": 1})
        self.assertEqual(response.status_code, 404)
