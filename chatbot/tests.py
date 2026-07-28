import json
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.test.utils import override_settings as override_django_settings

from .models import ChatMessage, ContactMessage, MenuItem


@override_django_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class ChatApiFallbackTests(TestCase):
    @override_settings(AGENT_ROUTER_API_KEY="test-key")
    @patch("chatbot.views.requests.post")
    def test_general_question_uses_agent_router_response(self, mock_post):
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "The Sun is a star at the center of our solar system."}}]
        }
        mock_post.return_value.raise_for_status.return_value = None

        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "What is the sun?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["reply"],
            "The Sun is a star at the center of our solar system.",
        )
        messages = mock_post.call_args.kwargs["json"]["messages"]
        self.assertIn("general-purpose helpful assistant", messages[0]["content"])
        self.assertIn("What is the sun?", messages[-1]["content"])

    @override_settings(AGENT_ROUTER_API_KEY="test-key")
    @patch("chatbot.views.requests.post")
    def test_empty_router_reply_returns_non_empty_fallback(self, mock_post):
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "   "}}]
        }
        mock_post.return_value.raise_for_status.return_value = None

        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Tell me about Python"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["reply"].strip())
        self.assertIn("general questions", body["reply"])

    @override_settings(AGENT_ROUTER_API_KEY="")
    def test_greeting_returns_a_helpful_local_reply(self):
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Hello there"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("reply", body)
        self.assertIn("BrewMind", body["reply"])
        self.assertGreaterEqual(ChatMessage.objects.count(), 2)

    @override_settings(AGENT_ROUTER_API_KEY="")
    def test_specials_question_uses_menu_data_when_router_is_unavailable(self):
        MenuItem.objects.create(
            name="Cappuccino",
            category="coffee",
            description="Classic espresso with frothy milk",
            price="180.00",
            is_special=True,
            is_available=True,
        )

        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "What's today's special?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("Cappuccino", body["reply"])

    def test_home_page_uses_local_image_fallback_for_menu_cards(self):
        MenuItem.objects.create(
            name="Cyan Latte",
            category="hot",
            description="A bright red-and-cyan café favorite",
            price="180.00",
            is_special=True,
            is_available=True,
            image_url="",
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cyan Latte")
        self.assertContains(response, "img/coffee-cup.svg")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_contact_form_saves_message_and_sends_email(self):
        response = self.client.post(
            "/contact/",
            {
                "name": "Asha",
                "email": "asha@example.com",
                "phone": "+919999999999",
                "message": "I would love to book a table for this weekend.",
                "website": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(ContactMessage.objects.filter(email="asha@example.com").exists())
        self.assertEqual(len(mail.outbox), 1)
