from django.db import models
import uuid


class ChatSession(models.Model):
    """A single visitor's chat session with BrewMind AI."""
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.session_id}"


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:40]}"


class MenuItem(models.Model):
    CATEGORY_CHOICES = (
        ("hot", "Hot Beverages"),
        ("cold", "Cold Beverages"),
        ("juice", "Fresh Juices"),
        ("snack", "Snacks"),
        ("dessert", "Desserts"),
    )
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    is_special = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    image_url = models.URLField(blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} (₹{self.price})"

    @property
    def category_icon(self):
        mapping = {
            "hot": "☕",
            "cold": "🥤",
            "juice": "🍹",
            "snack": "🥐",
            "dessert": "🍰",
        }
        return mapping.get(self.category, "🍽")

    @property
    def rating(self):
        return "4.8"

    @property
    def prep_time(self):
        mapping = {
            "Espresso": "5 min",
            "Cappuccino": "8 min",
            "Café Latte": "9 min",
            "Caramel Macchiato": "10 min",
            "Mocha": "9 min",
            "Flat White": "8 min",
            "Cold Coffee": "7 min",
            "Iced Latte": "7 min",
            "Matcha Latte": "10 min",
            "Frappe": "10 min",
            "Brownie": "6 min",
            "Cheesecake": "7 min",
            "Croissant": "12 min",
            "Muffin": "8 min",
            "Donut": "6 min",
            "Pancakes": "12 min",
            "Classic Pancakes": "12 min",
            "Club Sandwich": "10 min",
            "Hot Chocolate": "6 min",
            "Fresh Orange Juice": "5 min",
            "Watermelon Cooler": "6 min",
            "Mixed Berry Smoothie": "8 min",
            "Pineapple Ginger Zing": "6 min",
            "Mango Delight": "7 min",
            "French Fries": "9 min",
            "Nachos Supreme": "10 min",
            "Paneer Tikka Skewers": "14 min",
            "Cheesy Garlic Bread": "9 min",
            "Chocolate Donut": "5 min",
            "New York Cheesecake": "7 min",
        }
        return mapping.get(self.name, "8 min")

    @property
    def calories(self):
        mapping = {
            "Espresso": "5 kcal",
            "Cappuccino": "140 kcal",
            "Café Latte": "170 kcal",
            "Caramel Macchiato": "210 kcal",
            "Mocha": "230 kcal",
            "Flat White": "160 kcal",
            "Cold Coffee": "240 kcal",
            "Iced Latte": "180 kcal",
            "Matcha Latte": "190 kcal",
            "Frappe": "320 kcal",
            "Brownie": "280 kcal",
            "Cheesecake": "320 kcal",
            "Croissant": "260 kcal",
            "Muffin": "310 kcal",
            "Donut": "250 kcal",
            "Pancakes": "340 kcal",
            "Club Sandwich": "380 kcal",
        }
        return mapping.get(self.name, "-- kcal")

    @property
    def ingredients(self):
        mapping = {
            "Espresso": "Arabica beans, hot water",
            "Cappuccino": "Espresso, steamed milk, milk foam",
            "Café Latte": "Espresso, steamed milk, crema",
            "Caramel Macchiato": "Espresso, vanilla milk, caramel drizzle",
            "Mocha": "Espresso, chocolate, steamed milk, whipped cream",
            "Flat White": "Espresso, microfoam milk",
            "Cold Coffee": "Blended espresso, milk, ice, chocolate drizzle",
            "Iced Latte": "Espresso, cold milk, ice",
            "Matcha Latte": "Matcha powder, steamed milk, vanilla",
            "Frappe": "Coffee, ice, milk, caramel",
            "Brownie": "Chocolate, butter, sugar, eggs",
            "Cheesecake": "Cream cheese, berries, biscuit crust",
            "Croissant": "Flour, butter, milk, yeast",
            "Muffin": "Flour, chocolate chips, eggs, butter",
            "Donut": "Flour, sugar, yeast, glaze",
            "Pancakes": "Flour, eggs, milk, maple syrup",
            "Club Sandwich": "Bread, grilled chicken, lettuce, tomato, cheese",
        }
        return mapping.get(self.name, "Chef’s selection of premium ingredients")


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=150, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"
