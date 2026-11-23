"""Роль «Моделі». Готує базу до атаки; запускати можна скільки завгодно разів.

    python manage.py migrate
    python manage.py seed_attack

Атакувальник клонує ваш репозиторій на тегу `attack` і запускає саме ці дві команди,
тож усе, без чого атака неможлива, має створюватися тут.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import ParkingLevel, ParkingRequest

# Ті самі паролі — у contract.json.
ATTACKERS = {"attacker1": "attack-pass-1", "attacker2": "attack-pass-2"}


class Command(BaseCommand):
    help = "Акаунти attacker1/attacker2 і каталог для атаки."

    def handle(self, *args, **options):
        User = get_user_model()
        test_user_ids = []
        for username, password in ATTACKERS.items():
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.is_staff = False
            user.is_superuser = False
            user.is_active = True
            user.save()
            test_user_ids.append(user.pk)

        ParkingRequest.objects.filter(owner_id__in=test_user_ids).delete()

        levels = (
            (1, "Рівень -1", 50),
            (2, "Рівень 0", 50),
            (3, "Рівень 1", 50),
            (4, "Рівень 2", 1),
        )
        for level_id, name, available in levels:
            ParkingLevel.objects.update_or_create(
                pk=level_id,
                defaults={"name": name, "available": available},
            )

        self.stdout.write(
            self.style.SUCCESS("Готово: attacker1, attacker2 і місця паркінгу.")
        )
