import json
import os
from django.core.management.base import BaseCommand
from ecsite.models import Item, User


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--file", default="MOCK_DATA.json", help="JSON file name to load data from"
        )

    def handle(self, *args, **options):
        Item.objects.all().delete()
        User.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("All existing item data has been deleted"))

        try:
            file_name = options.get("file", "MOCK_DATA.json")
            json_file_path = os.path.join(os.path.dirname(__file__), file_name)

            with open(json_file_path) as json_file:
                data = json.load(json_file)
                items = [
                    Item(
                        name=item["name"],
                        price=item["price"],
                        quantity=item["quantity"],
                    )
                    for item in data
                ]
                Item.objects.bulk_create(items)

            User.objects.create_superuser(
                "testuser", email="testuser@example.com", password="testpassword"
            )
            for i in range(1, 6):
                User.objects.create_user(
                    f"testuser{i}",
                    email=f"testuser{i}@example.com",
                    password="testpassword",
                )

            self.stdout.write(
                self.style.SUCCESS(f"Mock data loaded successfully from {file_name}")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading data: {e}"))
