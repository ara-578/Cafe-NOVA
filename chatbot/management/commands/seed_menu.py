from django.core.management.base import BaseCommand
from chatbot.models import MenuItem

# (name, category, description, price_usd, is_special, image_url)
MENU_DATA = [
    # Hot Beverages
    ("Espresso", "hot", "A bold double shot pulled from single-origin Arabica beans.", 3.50, False,
     "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?auto=format&fit=crop&w=900&q=80"),
    ("Cappuccino", "hot", "Rich espresso crowned with velvety steamed milk foam.", 4.50, False,
     "https://images.unsplash.com/photo-1517701604599-bb29b565090c?auto=format&fit=crop&w=900&q=80"),
    ("Latte", "hot", "Smooth espresso layered with silky steamed milk and light crema.", 4.75, False,
     "https://images.unsplash.com/photo-1561882468-9110e03e0f78?auto=format&fit=crop&w=900&q=80"),
    ("Americano", "hot", "Espresso diluted with hot water for a clean, bold finish.", 3.75, False,
     "https://images.unsplash.com/photo-1551030173-122aabc4489c?auto=format&fit=crop&w=900&q=80"),
    ("Mocha", "hot", "Espresso, dark chocolate and steamed milk finished with whipped cream.", 5.25, True,
     "https://images.unsplash.com/photo-1541167760496-1628856ab772?auto=format&fit=crop&w=900&q=80"),
    ("Hot Chocolate", "hot", "Velvety Belgian chocolate melted into steamed milk, topped with marshmallows.", 4.25, False,
     "https://images.unsplash.com/photo-1542990253-0d0f5be5f0ed?auto=format&fit=crop&w=900&q=80"),

    # Cold Beverages
    ("Iced Latte", "cold", "Chilled espresso over cold milk and ice for a smooth refresh.", 4.95, False,
     "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?auto=format&fit=crop&w=900&q=80"),
    ("Cold Coffee", "cold", "Blended espresso, milk and ice topped with chocolate drizzle.", 4.75, False,
     "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=80"),
    ("Iced Mocha", "cold", "Chocolate, espresso and cold milk swirled over crushed ice.", 5.50, True,
     "https://images.unsplash.com/photo-1461988091159-192b6df7054f?auto=format&fit=crop&w=900&q=80"),
    ("Frappuccino", "cold", "Whipped coffee blended with ice and a caramel finish.", 5.75, False,
     "https://images.unsplash.com/photo-1517959105821-eaf2591984ca?auto=format&fit=crop&w=900&q=80"),
    ("Milkshake", "cold", "Creamy vanilla milkshake topped with whipped cream and a cherry.", 5.25, False,
     "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80"),

    # Fresh Juices
    ("Orange Juice", "juice", "Cold-pressed oranges, no added sugar, served chilled.", 3.95, False,
     "https://images.unsplash.com/photo-1613478223719-2ab802602423?auto=format&fit=crop&w=900&q=80"),
    ("Watermelon Juice", "juice", "Fresh watermelon blended with mint and a squeeze of lime.", 3.75, True,
     "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=900&q=80"),
    ("Mango Juice", "juice", "Seasonal Alphonso mango blended fresh and chilled.", 4.25, False,
     "https://images.unsplash.com/photo-1546173159-315724a31696?auto=format&fit=crop&w=900&q=80"),
    ("Lemon Mint", "juice", "Zesty lemon with fresh mint leaves, lightly sweetened.", 3.50, False,
     "https://images.unsplash.com/photo-1523371054106-bbf80586c38c?auto=format&fit=crop&w=900&q=80"),
    ("Pineapple Juice", "juice", "Fresh pineapple juice, naturally sweet and tangy.", 3.95, False,
     "https://images.unsplash.com/photo-1600271886742-f049cd451bba?auto=format&fit=crop&w=900&q=80"),
    ("Strawberry Velvet Latte", "hot", "Silky strawberry-infused latte with a rosy finish and velvet crema.", 5.95, True,
     "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?auto=format&fit=crop&w=900&q=80"),
    ("Berry Bliss Smoothie", "cold", "Mixed berry smoothie with yogurt, chia, and a bright citrus lift.", 5.25, False,
     "https://images.unsplash.com/photo-1502741338009-cac2772e18bc?auto=format&fit=crop&w=900&q=80"),
    ("Strawberry Citrus Juice", "juice", "A bright blend of strawberries, orange, and mint for a refreshing sip.", 4.15, False,
     "https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?auto=format&fit=crop&w=900&q=80"),
    ("Berry Tart", "dessert", "Buttery tart filled with lush berry compote and vanilla cream.", 6.40, False,
     "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=900&q=80"),

    # Snacks
    ("French Fries", "snack", "Crispy golden fries tossed in peri-peri seasoning.", 3.50, False,
     "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=900&q=80"),
    ("Veg Sandwich", "snack", "Grilled sandwich loaded with fresh vegetables and cheese.", 4.50, False,
     "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=900&q=80"),
    ("Chicken Sandwich", "snack", "Grilled chicken breast with lettuce, tomato and house sauce.", 5.75, False,
     "https://images.unsplash.com/photo-1567234669003-dce7a7a88821?auto=format&fit=crop&w=900&q=80"),
    ("Garlic Bread", "snack", "Toasted baguette loaded with garlic butter and molten cheese.", 3.95, False,
     "https://images.unsplash.com/photo-1573140401552-3fab0b24427f?auto=format&fit=crop&w=900&q=80"),
    ("Burger", "snack", "Juicy grilled patty with cheese, lettuce and our signature sauce.", 6.50, True,
     "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80"),
    ("Pizza Slice", "snack", "Wood-fired margherita slice with fresh basil and mozzarella.", 4.25, False,
     "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=900&q=80"),
    ("Pasta", "snack", "Creamy alfredo pasta tossed with herbs and parmesan.", 6.95, False,
     "https://images.unsplash.com/photo-1551183053-bf91a1d81141?auto=format&fit=crop&w=900&q=80"),
    ("Croissant", "snack", "Flaky, buttery and baked fresh every morning.", 3.25, False,
     "https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=900&q=80"),
    ("Muffins", "snack", "Loaded with juicy blueberries and a soft crumb.", 3.50, False,
     "https://images.unsplash.com/photo-1607958996333-41aef7caefaa?auto=format&fit=crop&w=900&q=80"),
    ("Brownies", "snack", "Fudgy dark-chocolate brownie with a crackly top.", 3.95, False,
     "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=900&q=80"),

    # Desserts
    ("Cheesecake", "dessert", "Creamy baked cheesecake on a buttery biscuit crust.", 5.95, True,
     "https://images.unsplash.com/photo-1567171466295-4afa63d45416?auto=format&fit=crop&w=900&q=80"),
    ("Chocolate Cake", "dessert", "Rich layered chocolate cake with a silky ganache.", 5.50, False,
     "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=900&q=80"),
    ("Tiramisu", "dessert", "Classic Italian layers, espresso-soaked and dusted with cocoa.", 6.25, True,
     "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=900&q=80"),
    ("Donuts", "dessert", "Soft glazed donuts dipped in rich chocolate ganache.", 2.95, False,
     "https://images.unsplash.com/photo-1551024506-0bccd828d307?auto=format&fit=crop&w=900&q=80"),
    ("Cupcakes", "dessert", "Vanilla sponge cupcakes topped with swirled buttercream.", 3.25, False,
     "https://images.unsplash.com/photo-1587668178277-295251f900ce?auto=format&fit=crop&w=900&q=80"),
    ("Cookies", "dessert", "Warm, chewy chocolate-chip cookies baked fresh daily.", 2.75, False,
     "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=900&q=80"),
]


class Command(BaseCommand):
    help = "Seed the database with Cafe Nova menu items (USD pricing)."

    def handle(self, *args, **options):
        created_count = 0
        for name, category, description, price, is_special, image_url in MENU_DATA:
            obj, created = MenuItem.objects.update_or_create(
                name=name,
                defaults={
                    "category": category,
                    "description": description,
                    "price": price,
                    "is_special": is_special,
                    "image_url": image_url,
                    "is_available": True,
                },
            )
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seeded menu: {created_count} new items created (total {MenuItem.objects.count()})."
        ))
