import json
import logging
import re
import time

import requests
from django.conf import settings
from django.core.management import call_command
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages as django_messages

from .models import ChatSession, ChatMessage, MenuItem, ContactMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are Velvet AI, the dedicated ordering & information assistant for BrewMind \
Cafe (Technopark, Trivandrum). You are NOT a general-purpose assistant.

STRICT SCOPE RULE (most important, never break this):
Only answer questions about:
1) BrewMind Cafe — the menu, prices, ingredients/allergens, today's specials, hours, \
   location, reservations, orders, the cart/checkout process, and small talk directed \
   at the cafe (greetings, thanks, "who are you").
2) Simple logical or arithmetic questions (e.g. basic math like "what is 12 + 7", \
   quick reasoning like "if I order 2 coffees at Rs.150 each, how much is that", or \
   comparisons like "which costs more, X or Y"). Answer these directly and briefly, \
   preferring cafe-related examples (totals, quantities, prices) where natural.

If the user asks anything outside those two areas — general knowledge, news, coding, \
other businesses, homework unrelated to simple math, or any topic unrelated to BrewMind \
Cafe or basic logic/arithmetic — do NOT answer it. Instead, politely say you're the \
BrewMind Cafe assistant and can only help with cafe questions and simple logical/math \
questions, then invite them to ask about the menu, hours, or their order. Keep the \
redirect short and friendly, never preachy or repetitive.

BrewMind Cafe facts:
- Hours: Mon-Sun, 8:00 AM - 10:00 PM.
- Location: Technopark, Trivandrum.

Today's menu:
{menu}
"""

def build_menu_text():
    items = MenuItem.objects.filter(is_available=True)
    if not items.exists():
        return "(Menu is being prepared - ask the staff for today's specials!)"
    lines = []
    for item in items:
        tag = " - Chef's special" if item.is_special else ""
        lines.append(f"- {item.name} ({item.get_category_display()}) - Rs. {item.price}{tag}")
    return "\n".join(lines)


def extract_router_reply(result):
    choices = result.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return (content or "").strip()


CAFE_KEYWORDS = [
    "cafe", "café", "brewmind", "menu", "coffee", "tea", "latte", "cappuccino",
    "espresso", "mocha", "milkshake", "juice", "pastry", "dessert", "cake",
    "sandwich", "snack", "breakfast", "lunch", "dinner", "meal", "food", "drink",
    "beverage", "burger", "ice cream", "sundae", "shake", "price", "cost", "rupee", "rs.", "special", "specials", "today's",
    "hour", "hours", "open", "opens", "closed", "closing", "timing", "timings",
    "location", "address", "where", "technopark", "trivandrum", "reservation",
    "book", "table", "seat", "order", "cart", "checkout", "coupon", "discount",
    "recommend", "suggest", "allerg", "vegan", "vegetarian", "spicy", "sweet",
    "cold", "hot", "iced", "contact", "staff", "waiter", "delivery", "takeaway",
    "velvet", "who are you", "your name", "thank", "thanks", "hello", "hi ",
    "hey", "good morning", "good afternoon", "good evening",
]

OFF_TOPIC_REDIRECT = (
    "I'm the BrewMind Cafe assistant, so I can only help with cafe questions "
    "(menu, prices, specials, hours, location, your order) or simple math — "
    "things like general knowledge or unrelated topics are outside what I "
    "can help with. What can I get started for you?"
)


def is_cafe_related(text):
    """Very small heuristic used only by the OFFLINE fallback (see
    build_local_reply) to decide whether a message is in-scope. The real
    scoping is enforced by the AgentRouter system prompt; this is just a
    safety net for when that API is unreachable."""
    return any(keyword in text for keyword in CAFE_KEYWORDS)


def try_simple_math(text):
    """Handles very simple arithmetic like 'what is 12 + 7' or '5*3' as a
    small logic-question allowance in the OFFLINE fallback. Returns a reply
    string, or None if the text isn't a simple math expression."""
    cleaned = text
    for phrase in ("what is", "what's", "calculate", "compute", "solve"):
        cleaned = cleaned.replace(phrase, "")
    cleaned = cleaned.strip()

    match = re.fullmatch(
        r"(-?\d+(?:\.\d+)?)\s*([+\-*/x×])\s*(-?\d+(?:\.\d+)?)", cleaned
    )
    if not match:
        return None

    a, op, b = match.group(1), match.group(2), match.group(3)
    a, b = float(a), float(b)
    try:
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op in ("*", "x", "×"):
            result = a * b
        elif op == "/":
            if b == 0:
                return "That would be dividing by zero, which isn't defined."
            result = a / b
        else:
            return None
    except Exception:
        return None

    if result == int(result):
        result = int(result)
    return f"{a:g} {op} {b:g} = {result}"


CATEGORY_LABELS = {
    "hot": "Hot Beverages",
    "cold": "Cold Beverages",
    "juice": "Fresh Juices",
    "snack": "Snacks",
    "dessert": "Desserts",
}

CATEGORY_ALIASES = {
    "hot": ["hot", "coffee", "coffees", "espresso", "cappuccino", "latte", "mocha",
            "americano", "hot chocolate", "hot beverage", "hot drink"],
    "cold": ["cold", "iced", "ice", "frappuccino", "frappe", "cold coffee", "cold drink",
             "cold beverage", "milkshake", "shake"],
    "juice": ["juice", "juices", "smoothie", "smoothies"],
    "snack": ["snack", "snacks", "sandwich", "burger", "fries", "pizza", "pasta",
              "croissant", "muffin", "brownie", "garlic bread"],
    "dessert": ["dessert", "desserts", "sweet", "sweets", "cake", "cheesecake",
                "tiramisu", "ice cream", "cupcake", "cookie"],
}


def find_menu_item(text, menu_items):
    """Best-effort match of a menu item name inside free-form user text."""
    best = None
    best_len = 0
    for item in menu_items:
        name = item.name.lower()
        if name in text and len(name) > best_len:
            best = item
            best_len = len(name)
    return best


def find_category(text):
    for category, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text):
                return category
    return None


def format_item_price(item):
    return f"Rs. {item.price:g}" if float(item.price) == int(item.price) else f"Rs. {item.price}"


def build_local_reply(user_message, menu_items):
    """
    Last-resort OFFLINE fallback, only used when the AgentRouter API call
    fails entirely (see chat_api below). Strictly cafe-only plus simple
    logic/math, matching the AI's own scope rules: any other message gets
    politely redirected instead of answered. Unlike a generic template
    reply, this looks up real menu data (name, price, ingredients,
    calories, specials) so answers are actually correct for what was asked.
    """
    text = re.sub(r"\s+", " ", (user_message or "")).strip().lower()
    text = text.rstrip("?!. ")

    if not text:
        return "Hi there! I'm Velvet AI from BrewMind Cafe. Ask me about our menu, hours, or today's specials."

    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
    if any(text == g or text.startswith(g + " ") for g in greetings):
        return "Hi there! I'm Velvet AI from BrewMind Cafe. Ask me about our menu, prices, hours, or today's specials."

    if any(keyword in text for keyword in ["who are you", "your name", "are you velvet"]):
        return "I'm Velvet AI, the BrewMind Cafe assistant — here to help with our menu, hours, and your order."

    if any(keyword in text for keyword in ["thank you", "thanks"]):
        return "You're very welcome — happy to help with your next cafe craving."

    math_reply = try_simple_math(text)
    if math_reply:
        return math_reply

    # --- Specific item lookup: price / ingredients / calories / prep time ---
    # Checked before the off-topic gate, since item names (e.g. "tiramisu")
    # aren't in the generic CAFE_KEYWORDS list but are obviously in-scope.
    matched_item = find_menu_item(text, menu_items)

    if not matched_item and not is_cafe_related(text):
        return OFF_TOPIC_REDIRECT

    if matched_item:
        if any(k in text for k in ["ingredient", "made of", "contain", "what's in", "whats in", "allerg"]):
            return f"{matched_item.name} is made with {matched_item.ingredients}. Let me know if you have any specific allergy concerns and I'll double-check with the kitchen."
        if any(k in text for k in ["calorie", "calories", "kcal"]):
            return f"{matched_item.name} has approximately {matched_item.calories}."
        if any(k in text for k in ["how long", "prep time", "ready", "wait"]):
            return f"{matched_item.name} usually takes about {matched_item.prep_time} to prepare."
        if any(k in text for k in ["price", "cost", "how much", "rate"]):
            return f"{matched_item.name} is priced at {format_item_price(matched_item)}."
        # Generic mention of the item name -> give a full quick summary
        special_note = " It's one of today's Chef's specials!" if matched_item.is_special else ""
        return (
            f"{matched_item.name} ({CATEGORY_LABELS.get(matched_item.category, matched_item.category)}) "
            f"is {format_item_price(matched_item)}. {matched_item.description}{special_note}"
        )

    if "special" in text and ("today" in text or "specials" in text or text == "special"):
        specials = list(menu_items.filter(is_special=True, is_available=True))
        if specials:
            names = ", ".join(f"{item.name} ({format_item_price(item)})" for item in specials)
            return f"Today's Chef's specials are: {names}. Want me to tell you more about any of these?"
        return "Our kitchen is brewing something lovely today - ask me for a coffee, pastry, or a cozy recommendation."

    if any(keyword in text for keyword in ["hour", "hours", "open", "closed", "timing", "time"]):
        return "BrewMind Cafe is open daily from 8:00 AM to 10:00 PM, and we're located in Technopark, Trivandrum."

    if any(keyword in text for keyword in ["location", "address", "where", "technopark"]):
        return "You'll find us at Technopark, Trivandrum, the perfect spot for your next coffee break."

    # --- Category listing, e.g. "what juices do you have", "show me desserts" ---
    category = find_category(text)
    if category:
        items = list(menu_items.filter(category=category))
        if items:
            names = ", ".join(f"{item.name} ({format_item_price(item)})" for item in items)
            label = CATEGORY_LABELS.get(category, category)
            return f"Our {label} lineup: {names}. Want details on any of these?"
        return f"We don't have any {CATEGORY_LABELS.get(category, category)} available right now, but I'm happy to suggest something else."

    if any(keyword in text for keyword in ["price", "cost", "cheap", "expensive", "rupee", "rupees"]):
        cheapest = menu_items.order_by("price").first()
        priciest = menu_items.order_by("-price").first()
        if cheapest and priciest:
            return (
                f"Prices range from {format_item_price(cheapest)} ({cheapest.name}) to "
                f"{format_item_price(priciest)} ({priciest.name}). Ask me about a specific item and I'll give you the exact price."
            )
        return "Ask me for a specific item and I'll give you the exact price."

    if any(keyword in text for keyword in ["menu", "what do you have", "what do you serve", "options"]):
        by_category = {}
        for item in menu_items:
            by_category.setdefault(item.category, []).append(item.name)
        parts = [f"{CATEGORY_LABELS.get(cat, cat)}: {', '.join(names[:4])}" for cat, names in by_category.items()]
        if parts:
            return "Here's what we have — " + " | ".join(parts) + ". Ask about any item for price and details."
        return "I can help you choose from our coffee, tea, pastries, meals, and desserts. Tell me what you're craving."

    if any(keyword in text for keyword in ["recommend", "suggest", "drink", "coffee", "tea", "pastry", "dessert",
                                            "food", "meal", "sweet", "savory", "cold", "hungry", "thirsty"]):
        pool = menu_items
        if "sweet" in text or "dessert" in text:
            pool = menu_items.filter(category="dessert") or pool
        elif "cold" in text or "thirsty" in text:
            pool = menu_items.filter(category__in=["cold", "juice"]) or pool
        elif "hungry" in text or "savory" in text:
            pool = menu_items.filter(category="snack") or pool
        item_names = ", ".join(item.name for item in list(pool)[:5])
        if item_names:
            return f"A few favorites are {item_names}. Tell me whether you want something sweet, cozy, or energizing and I'll narrow it down further."
        return "I can help you choose from our coffee, tea, pastries, meals, and desserts. Tell me what you're craving."

    if any(keyword in text for keyword in ["reservation", "book", "table", "seat"]):
        return "We'd love to welcome you in - ask us about reservations and we can help you plan your visit."

    return "I'm the BrewMind Cafe assistant — ask me about the menu, prices, hours, or today's specials and I'll help right away."

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

    last_exc = None
    last_status = None
    last_body = ""

    # Try up to 3 times — handles transient network blips / rate limits
    # without immediately dumping the user into the offline fallback.
    for attempt in range(3):
        try:
            response = requests.post(
                settings.AGENT_ROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=45,
            )
            last_status = response.status_code
            last_body = response.text[:500]

            if response.status_code == 200:
                result = response.json()
                reply = extract_router_reply(result)
                if not reply:
                    raise ValueError("Agent Router returned an empty reply.")
                ChatMessage.objects.create(session=chat_session, role="assistant", content=reply)
                return JsonResponse({"reply": reply})

            if response.status_code == 429 and attempt < 2:
                # Rate limited — brief backoff, then retry.
                time.sleep(1.5 * (attempt + 1))
                continue

            response.raise_for_status()

        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
                continue
            break
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            last_exc = exc
            break

    # Every attempt failed — log the real cause server-side so it shows up
    # in `runserver` output / your hosting logs, then fall back gracefully.
    logger.error(
        "AgentRouter call failed after retries. status=%s body=%s exc=%s",
        last_status, last_body, last_exc,
    )

    reply = build_local_reply(user_message, menu_items)
    ChatMessage.objects.create(session=chat_session, role="assistant", content=reply)

    error_detail = last_exc and str(last_exc) or f"HTTP {last_status}: {last_body}"
    response_payload = {"reply": reply}
    if settings.DEBUG:
        # Only leak the raw error to the browser in DEBUG mode, so you can
        # see exactly why the AI call failed (bad key, wrong URL, 401, etc.)
        # without exposing internals in production.
        response_payload["error"] = error_detail
    return JsonResponse(response_payload, status=200)

