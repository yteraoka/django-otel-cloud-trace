import datetime

from django.test import TestCase
from django.utils import timezone

from polls.models import Choice, Question


def create_question(question_text, days):
    """Create a question published ``days`` offset to now (negative for the past)."""
    return Question.objects.create(
        question_text=question_text,
        pub_date=timezone.now() + datetime.timedelta(days=days),
    )


class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        """was_published_recently() is False for questions with a future pub_date."""
        future_question = Question(pub_date=timezone.now() + datetime.timedelta(days=30))
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        """was_published_recently() is False for questions older than one day."""
        old_question = Question(pub_date=timezone.now() - datetime.timedelta(days=1, seconds=1))
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        """was_published_recently() is True for questions published within the last day."""
        recent_question = Question(
            pub_date=timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        )
        self.assertIs(recent_question.was_published_recently(), True)

    def test_str(self):
        question = create_question("What's new?", days=-1)
        self.assertEqual(str(question), "What's new?")


class ChoiceModelTests(TestCase):
    def test_str(self):
        question = create_question("What's new?", days=-1)
        choice = Choice.objects.create(question=question, choice_text="Not much")
        self.assertEqual(str(choice), "Not much")

    def test_votes_default_to_zero(self):
        question = create_question("What's new?", days=-1)
        choice = Choice.objects.create(question=question, choice_text="Not much")
        self.assertEqual(choice.votes, 0)

    def test_choices_are_deleted_with_their_question(self):
        question = create_question("What's new?", days=-1)
        Choice.objects.create(question=question, choice_text="Not much")
        question.delete()
        self.assertEqual(Choice.objects.count(), 0)
