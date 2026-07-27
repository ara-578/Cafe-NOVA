document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chatForm');
  if (!chatForm) return;

  const chatBody = document.getElementById('chatBody');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const suggestions = document.querySelectorAll('.suggestion-chip');

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  function scrollToBottom() {
    if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;
  }

  function addMessage(text, sender) {
    if (!chatBody) return;
    const msg = document.createElement('div');
    msg.className = `msg msg-${sender}`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    msg.appendChild(bubble);
    chatBody.appendChild(msg);
    scrollToBottom();
  }

  function showTyping() {
    if (!chatBody) return;
    const msg = document.createElement('div');
    msg.className = 'msg msg-bot';
    msg.id = 'typingIndicator';
    msg.innerHTML = '<div class="bubble typing-dots"><span></span><span></span><span></span></div>';
    chatBody.appendChild(msg);
    scrollToBottom();
  }

  function removeTyping() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
  }

  async function sendMessage(text) {
    if (!text.trim()) return;

    addMessage(text, 'user');
    if (chatInput) chatInput.value = '';
    if (sendBtn) sendBtn.disabled = true;
    showTyping();

    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken || '',
        },
        body: JSON.stringify({ message: text }),
      });

      const data = await response.json();
      removeTyping();
      addMessage(data.reply || 'Sorry, something went wrong. Please try again. ☕', 'bot');
    } catch (err) {
      removeTyping();
      addMessage('☕ Velvet AI is currently brewing fresh ideas. Please try again in a moment.', 'bot');
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (chatInput) chatInput.focus();
    }
  }

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (chatInput) sendMessage(chatInput.value);
  });

  suggestions.forEach((chip) => {
    chip.addEventListener('click', () => sendMessage(chip.textContent));
  });

  const contactForm = document.getElementById('contactForm');
  const contactSubmit = document.getElementById('contactSubmit');
  if (contactForm && contactSubmit) {
    contactForm.addEventListener('submit', () => {
      contactForm.classList.add('is-submitting');
      contactSubmit.textContent = 'Sending...';
    });
  }

  const revealItems = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('is-visible');
    });
  }, { threshold: 0.15 });
  revealItems.forEach((item) => observer.observe(item));

  const addToCartButtons = document.querySelectorAll('[data-add-to-cart]');
  const cartItems = document.getElementById('cartItems');
  const subtotalEl = document.getElementById('subtotal');
  const discountEl = document.getElementById('discount');
  const grandTotalEl = document.getElementById('grandTotal');
  const couponInput = document.getElementById('couponInput');
  const applyCoupon = document.getElementById('applyCoupon');

  let cart = [];
  let discount = 0;

  function renderCart() {
    if (!cartItems) return;
    if (cart.length === 0) {
      cartItems.innerHTML = '<p class="cart-empty">Your curated order is waiting.</p>';
    } else {
      cartItems.innerHTML = cart.map((item) => `
        <div class="cart-item">
          <span>${item.name}</span>
          <span>$${item.price.toFixed(2)}</span>
        </div>
      `).join('');
    }

    const subtotal = cart.reduce((sum, item) => sum + item.price, 0);
    const total = Math.max(0, subtotal + 2.5 - discount);
    if (subtotalEl) subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
    if (discountEl) discountEl.textContent = `$${discount.toFixed(2)}`;
    if (grandTotalEl) grandTotalEl.textContent = `$${total.toFixed(2)}`;
  }

  addToCartButtons.forEach((button) => {
    button.addEventListener('click', () => {
      cart.push({
        name: button.dataset.name,
        price: Number(button.dataset.price),
      });
      renderCart();
    });
  });

  if (applyCoupon && couponInput) {
    applyCoupon.addEventListener('click', () => {
      const code = couponInput.value.trim().toLowerCase();
      discount = code === 'nova10' ? 3 : 0;
      renderCart();
    });
  }

  renderCart();

  const testimonialCards = document.querySelectorAll('.testimonial-card');
  let testimonialIndex = 0;
  if (testimonialCards.length > 1) {
    setInterval(() => {
      testimonialCards.forEach((card) => card.classList.remove('active'));
      testimonialIndex = (testimonialIndex + 1) % testimonialCards.length;
      testimonialCards[testimonialIndex].classList.add('active');
    }, 5000);
  }
});
