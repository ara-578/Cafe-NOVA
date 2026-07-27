import json
import re

import requests
from django.conf import settings
from django.core.management import call_command
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages as django_messages

from .models import ChatSession, ChatMessage, MenuItem, ContactMessage

SYSTEM_PROMPT_TEMPLATE = """You are Velvet AI, the friendly AI barista and host of BrewMind Café — \
a cozy, modern café known for its handcrafted coffee, fresh pastries and warm vibes.

Your job:
- Greet guests warmly and help them explore the menu.
- Recommend food/drinks based on mood, taste, weather, or dietary needs.
- Answer questions about ingredients, prices, café hours, and reservations.
- Keep replies short, warm, and conversational (2-4 sentences), with the occasional \
coffee-themed emoji (☕ 🍰 🥐) — never overdo it.
- If asked something totally unrelated to the café, gently steer back to how you can help \
with food, drinks, or the café experience.

Café hours: Mon-Sun, 8:00 AM - 10:00 PM.
Location: Technopark, Trivandrum.

Here is today's menu you can reference:
{menu}
"""


def build_menu_text():
    items = MenuItem.objects.filter(is_available=True)
    if not items.exists():
        return "(Menu is being freshly brewed — ask the staff for today's specials!)"
    lines = []
    for item in items:
        tag = " ⭐ Chef's special" if item.is_special else ""
        lines.append(f"- {item.name} ({item.get_category_display()}) — ₹{item.price}{tag}")
    return "\n".join(lines)


def build_local_reply(user_message, menu_items):
    text = re.sub(r"\s+", " ", (user_message or "")).strip().lower()

    if not text:
        return "Hi there! I’m Velvet AI ☕ I can help with the menu, recommendations, or café details at BrewMind Café."

    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
    if any(greeting in text for greeting in greetings):
        return "Hi there! I’m Velvet AI ☕ I can help with today’s specials, drink picks, or anything about BrewMind Café."

    if "special" in text and ("today" in text or "specials" in text):
        specials = list(menu_items.filter(is_special=True, is_available=True)[:3])
        if specials:
            names = ", ".join(item.name for item in specials)
            return f"Today’s featured picks are {names}. I can also suggest a drink or pastry based on your mood ☕"
        return "Our kitchen is brewing something lovely today — ask me for a coffee, pastry, or a cozy recommendation."

    if any(keyword in text for keyword in ["hour", "hours", "open", "closed", "timing", "time"]):
        return "BrewMind Café is open daily from 8:00 AM to 10:00 PM, and we’re located in Technopark, Trivandrum."

    if any(keyword in text for keyword in ["location", "address", "where", "technopark"]):
        return "You’ll find us at Technopark, Trivandrum — the perfect spot for your next coffee break."

    if any(keyword in text for keyword in ["price", "cost", "cheap", "expensive", "rupee", "₹"]):
        return "Our menu has something for every mood and budget, from quick coffees to hearty café meals. Ask me for a specific item and I’ll guide you."

    if any(keyword in text for keyword in ["recommend", "drink", "coffee", "tea", "pastry", "dessert", "food", "meal", "sweet", "savory", "cold", "menu"]):
        item_names = ", ".join(item.name for item in menu_items[:5])
        if item_names:
            return f"A few favorites from our menu are {item_names}. Tell me whether you want something sweet, cozy, or energizing and I’ll narrow it down."
        return "I can help you choose from our coffee, tea, pastries, meals, and desserts. Tell me what you’re craving."

    if any(keyword in text for keyword in ["reservation", "book", "table", "seat"]):
        return "We’d love to welcome you in — ask us about reservations and we can help you plan your visit."

    if any(keyword in text for keyword in ["who are you", "your name", "velvet"]):
        return "I’m Velvet AI, your friendly AI barista at BrewMind Café ☕ I can help with drinks, food, and café details."

    if any(keyword in text for keyword in ["thank", "thanks"]):
        return "You’re very welcome ☕ I’m happy to help with your next café craving."

    return "I’m Velvet AI at BrewMind Café ☕ I can help with the menu, recommendations, café hours, or anything else about your visit. What would you like to know?"


def ensure_menu_items():
    """Seed a default menu when the database is empty so the landing page always has content."""
    if MenuItem.objects.filter(is_available=True).exists():
        return MenuItem.objects.filter(is_available=True)

    call_command("seed_menu")
    return MenuItem.objects.filter(is_available=True)


def home(request):
    """Landing page with hero, menu preview and embedded chatbot."""
    if "chat_session_id" not in request.session:
        session = ChatSession.objects.create()
        request.session["chat_session_id"] = str(session.session_id)

    menu_items = ensure_menu_items()
    specials = menu_items.filter(is_special=True)

    context = {
        "menu_items": menu_items,
        "specials": specials,
    }
    return render(request, "chatbot/index.html", context)


def menu_page(request):
    menu_items = ensure_menu_items()
    return render(request, "chatbot/menu.html", {"menu_items": menu_items})


def contact_page(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()
        honey = request.POST.get("website", "").strip()
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        def respond(ok, text):
            if is_ajax:
                return JsonResponse({"ok": ok, "message": text})
            django_messages.success(request, text) if ok else django_messages.error(request, text)
            return redirect("contact")

        if honey:
            return respond(False, "Your submission was flagged as spam.")

        if not all([name, email, message]):
            return respond(False, "Please fill in your name, email, and message.")

        # Prevent duplicate submissions: same email + message within the last 2 minutes.
        from django.utils import timezone
        from datetime import timedelta
        recent_duplicate = ContactMessage.objects.filter(
            email=email, message=message, created_at__gte=timezone.now() - timedelta(minutes=2)
        ).exists()
        if recent_duplicate:
            return respond(False, "You've already sent this message. Our team will get back to you shortly.")

        try:
            ContactMessage.objects.create(
                name=name, email=email, phone=phone, subject=subject, message=message
            )
            send_mail(
                subject=f"New Café Nova enquiry: {subject or 'General Enquiry'} — from {name}",
                message=(
                    f"Name: {name}\nEmail: {email}\nPhone: {phone or 'Not provided'}\n"
                    f"Subject: {subject or 'Not provided'}\n\nMessage:\n{message}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_RECEIVER_EMAIL],
                fail_silently=False,
            )
            return respond(True, "Thanks for reaching out! Your message has been sent to Café Nova.")
        except Exception:
            return respond(False, "We could not send your message right now. Please try again in a moment.")

    return render(request, "chatbot/contact.html")


@require_POST
def chat_api(request):
    """
    AI chat endpoint — proxies user messages to the Agent Router API
    (OpenAI-compatible chat completions format) using AGENT_ROUTER_API_KEY.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    user_message = (data.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message cannot be empty."}, status=400)

    session_id = request.session.get("chat_session_id")
    if session_id:
        chat_session, _ = ChatSession.objects.get_or_create(session_id=session_id)
    else:
        chat_session = ChatSession.objects.create()
        request.session["chat_session_id"] = str(chat_session.session_id)

    ChatMessage.objects.create(session=chat_session, role="user", content=user_message)
    menu_items = MenuItem.objects.filter(is_available=True)

    if not settings.AGENT_ROUTER_API_KEY:
        reply = build_local_reply(user_message, menu_items)
        ChatMessage.objects.create(session=chat_session, role="assistant", content=reply)
        return JsonResponse({"reply": reply})

    history_qs = chat_session.messages.order_by("-created_at")[:12]
    history = list(reversed(history_qs))

    messages_payload = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(menu=build_menu_text())}
    ]
    for msg in history:
        role = "assistant" if msg.role == "assistant" else "user"
        messages_payload.append({"role": role, "content": msg.content})

    headers = {
        "Authorization": f"Bearer {settings.AGENT_ROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.AGENT_ROUTER_MODEL,
        "messages": messages_payload,
        "temperature": 0.8,
        "max_tokens": 400,
    }

    try:
        response = requests.post(
            settings.AGENT_ROUTER_BASE_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as exc:
        reply = build_local_reply(user_message, menu_items)
        ChatMessage.objects.create(session=chat_session, role="assistant", content=reply)
        return JsonResponse({"reply": reply, "error": str(exc)}, status=200)
    except (KeyError, IndexError, ValueError):
        reply = build_local_reply(user_message, menu_items)
        ChatMessage.objects.create(session=chat_session, role="assistant", content=reply)
        return JsonResponse({"reply": reply}, status=200)

    ChatMessage.objects.create(session=chat_session, role="assistant", content=reply)
    return JsonResponse({"reply": reply})
