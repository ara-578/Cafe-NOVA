<<<<<<< HEAD
# Cafe Nova 🍵 — with Velvet AI
=======
# Cafe NOVA
🍵 — with Velvet AI
>>>>>>> 32539cb6f48371f8b5bc1aaed5d747d51bbbbb8e

A cozy, glassmorphism-styled café website built with Django, featuring **Velvet AI**,
an AI barista chatbot powered by the **Agent Router** API.

## Features
- Responsive glassmorphism UI (cute café theme, purple/cream/pink palette)
- Django backend with SQLite database (menu items, chat history, contact messages)
- Live AI chatbot widget ("Velvet AI") calling Agent Router's chat-completions API
- Menu page with categories & daily specials, contact form, Django admin

## 1. Setup

```bash
cd brewmind
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Generate a secret key (recommended for production)

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Set the output as `DJANGO_SECRET_KEY`.

## 3. Configure your Agent Router API key

Copy `.env.example` to `.env`, or export directly:

```bash
export AGENT_ROUTER_API_KEY="sk-your-agent-router-key-here"
```

Optional overrides:
```bash
export AGENT_ROUTER_BASE_URL="https://agentrouter.org/v1/chat/completions"
export AGENT_ROUTER_MODEL="gpt-4o-mini"
```

> If a `.env` file is used, load it before `manage.py runserver`, e.g. with
> `python -m pip install python-dotenv` and `from dotenv import load_dotenv; load_dotenv()`
> added to `config/settings.py`, or simply `export $(cat .env | xargs)` in your shell.

## 4. Database setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_menu        # loads sample café menu items
python manage.py createsuperuser  # optional, for /admin/
```

## 5. Run

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** — the home page, menu, contact page, and the
Velvet AI chat widget (bottom of the home page / `#chat`) will all be live.

## Project structure
```
brewmind/
├── config/            # Django project settings, urls, wsgi/asgi
├── chatbot/           # Main app: models, views, chat API, admin, seed command
├── templates/chatbot/ # HTML templates (base, index, menu, contact)
├── static/css/style.css
├── static/js/chat.js
├── requirements.txt
└── .env.example
```

## How the chatbot works
`chatbot/views.py` → `chat_api` receives the user's message, stores it in the
DB, builds a system prompt (with today's live menu injected), and POSTs to
`AGENT_ROUTER_BASE_URL` in OpenAI-compatible chat-completions format using
your `AGENT_ROUTER_API_KEY` as a Bearer token. The reply is stored and
returned as JSON to the frontend, rendered by `static/js/chat.js`.

If no API key is set, the chatbot still responds (gracefully telling you to
configure the key) instead of crashing — so the site stays functional out of
the box.

## Deploying
- `whitenoise` is already wired up for static file serving.
- Set `DJANGO_DEBUG=False` and a real `DJANGO_SECRET_KEY` in production.
- Run `python manage.py collectstatic` before deploying.
