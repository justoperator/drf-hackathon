# INSTRUCTION.md

Цей документ пояснює, як працює проєкт паркінгу, які запити він приймає
і що відбувається всередині кожної перевірки. Він призначений для підготовки
до демо та для відповідей команди на запитання про чужий код.

## 1. Про що цей проєкт

Проєкт відповідає за бронювання місць на рівні паркінгу.

Обмежений ресурс — поле `available` у моделі `ParkingLevel`. Це кількість вільних
місць конкретного рівня.

Користувач створює заявку `ParkingRequest`. Заявка містить:

- власника — `owner`;
- рівень паркінгу — `level`;
- кількість місць — `quantity`;
- стан — `status`.

Можливі стани заявки:

```text
draft ── confirm ──► confirmed ── cancel ──► cancelled
  └──────────── cancel ──────────────────────► cancelled
```

- `draft`: заявка створена, але місця ще не заброновані;
- `confirmed`: місця заброновані і рахуються зайнятими;
- `cancelled`: заявка скасована і більше не є активною.

Головний інваріант:

> Кількість місць зайнята тоді й лише тоді, коли заявка має стан `confirmed`.

Наприклад, заявка на 2 місця переводиться в `confirmed`: залишок рівня
зменшується рівно на 2. Переводиться в `cancelled`: залишок знову збільшується
рівно на 2. Для заявки зі станом `draft` скасування не змінює залишок.

## 2. Як запустити проєкт

Потрібно два вікна PowerShell.

Перше вікно:

```powershell
cd C:\Users\User\Desktop\starter
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_attack
python manage.py runserver 127.0.0.1:8000
```

Сервер має залишитися запущеним у першому вікні.

Друге вікно:

```powershell
cd C:\Users\User\Desktop\starter
.\.venv\Scripts\Activate.ps1
py -3.13 tools\attack_open.py --only 1,2,3,7,8,18,19
```

У [contract.json](C:/Users/User/Desktop/starter/contract.json) адреса сервер
має бути:

```json
"base_url": "http://127.0.0.1:8000"
```

## 3. Загальна схема запитів

Головні адреси:

| Запит | Адреса |
|---|---|
| Отримати JWT-токен | `POST /api/v1/auth/token/` |
| Оновити JWT-токен | `POST /api/v1/auth/token/refresh/` |
| Список рівнів | `GET /api/v1/levels/` |
| Один рівень | `GET /api/v1/levels/<id>/` |
| Список заявок поточного користувача | `GET /api/v1/parking-requests/` |
| Створити заявку | `POST /api/v1/parking-requests/` |
| Отримати одну свою заявку | `GET /api/v1/parking-requests/<id>/` |
| Підтвердити заявку | `POST /api/v1/parking-requests/<id>/confirm/` |
| Скасувати заявку | `POST /api/v1/parking-requests/<id>/cancel/` |

Маршрути реєструються у [api/urls.py](C:/Users/User/Desktop/starter/api/urls.py)
через `DefaultRouter`.

[config/urls.py](C:/Users/User/Desktop/starter/config/urls.py) підключає їх
під префіксом `/api/v1/`.

## 4. Як отримати токен

Запит:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/token/ `
  -H "Content-Type: application/json" `
  -d "{\"username\":\"attacker1\",\"password\":\"attack-pass-1\"}"
```

Приклад відповіді:

```json
{
  "refresh": "...",
  "access": "..."
}
```

Далі використовується поле `access`:

```text
Authorization: Bearer <access>
```

Токен живе 8 годин. Це налаштовано у `SIMPLE_JWT`
у [config/settings.py](C:/Users/User/Desktop/starter/config/settings.py).

Refresh-токен оновлює access-токен адресою:

```text
POST /api/v1/auth/token/refresh/
```

## 5. Запити до каталогу рівнів

### Отримати всі рівні

```text
GET /api/v1/levels/
```

Цей запит доступний без токена.

Приклад результату:

```json
[
  {
    "id": 1,
    "name": "Рівень -1",
    "available": 50
  }
]
```

`id` — номер рівня.

`name` — назва рівня.

`available` — кількість вільних місць.

### Отримати один рівень

```text
GET /api/v1/levels/4/
```

Кожен запит повертає актуальний залишок із бази даних.

Усі поля каталогового серіалізатора read-only:

- клієнт не може змінити назву через API;
- клієнт не може змінити `available` через API;
- зміна залишку дозволена тільки логікою серверних сервісів.

## 6. Запити до заявок

Усі запити до заявок потребують JWT-токена.

### Отримати список своїх заявок

```text
GET /api/v1/parking-requests/
Authorization: Bearer <access>
```

ViewSet фільтрує записи:

```python
ParkingRequest.objects.filter(owner=self.request.user)
```

Тому користувач не отримує заявки іншого користувача.

### Створити заявку

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/parking-requests/ `
  -H "Authorization: Bearer <ACCESS_TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"level\":4,\"quantity\":1}"
```

Тіло має містити:

```json
{
  "level": 4,
  "quantity": 1
}
```

При успіху сервер повертає `201 Created`:

```json
{
  "id": 1,
  "owner": 1,
  "level": 4,
  "quantity": 1,
  "status": "draft"
}
```

Важливо:

- користувач не передає поле `owner`;
- користувач не передає поле `status`;
- `owner` встановлюється сервером у `perform_create()`;
- `status` завжди починається з `draft`;
- створення заявки не змінює залишок;

Виклик із підміненими полями:

```json
{
  "level": 4,
  "quantity": 1,
  "owner": 2,
  "status": "confirmed"
}
```

не присвоює заявці власника другого користувача і не підтверджує її.

### Отримати конкретну заявку

```text
GET /api/v1/parking-requests/<id>/
```

Якщо заявка належить поточному користувачу — повертається `200`.

Якщо чужа або неіснує — очікується `403` або `404`.

Сервер не повинен показати дані чужої заявки.

### Змінити draft-заявку

Для заявки зі станом `draft` доступні `PATCH` і `PUT`.

Приклад:

```text
PATCH /api/v1/parking-requests/<id>/
```

Змінити можна поле `level` і `quantity`.

Для заявки зі станом `confirmed` або `cancelled` зміни повертають `409`.

Поле `status` read-only і не змінюється цим запитом.

### Видалити заявку

```text
DELETE /api/v1/parking-requests/<id>/
```

Дозволене видалення draft-заявки.

Підтверджену або скасовану заявку видаляти не дозволено:

- очікувана відповідь для них — `409`;
- їх має скасувати окрема action-функція `cancel`.

## 7. Підтвердження заявки

Запит:

```text
POST /api/v1/parking-requests/<id>/confirm/
Authorization: Bearer <access>
```

Приклад у PowerShell:

```powershell
curl.exe -X POST `
  http://127.0.0.1:8000/api/v1/parking-requests/1/confirm/ `
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Заяву може підтвердити тільки її власник.

Усі перевірки виконуються у [api/services.py](C:/Users/User/Desktop/starter/api/services.py).

Послідовність:

1. Відкрити заявку і заблокувати її рядок бази.
2. Перевірити власника.
3. Перевірити стан — він має бути `draft`.
4. Перевірити кількість — вона має бути додатною.
5. В умовному SQL-UPDATE перевірити достатню кількість місць.
6. Зменшити `available` у рівні.
7. Змінити стан заявки на `confirmed`.

Приклад умови списання:

```python
ParkingLevel.objects.filter(
    pk=parking_request.level_id,
    available__gte=parking_request.quantity,
).update(
    available=F("available") - parking_request.quantity
)
```

`available__gte=quantity` означає:

> Зменшити залишок, тільки якщо після перевірки у базі місць вистачає.

`F("available") - quantity` змушує базу оновлювати поточний числовий
залишок, а не локальне значення Python.

Результат `update()` дорівнює кількості змінених рядків:

- `1` — місця зарезервовано;
- `0` — місць недостатньо.

Успішна відповідь — `200`.

Повторний `confirm` повертає `409`, бо стан уже `confirmed`.

Якщо заявка `cancelled`, повторний `confirm` також повертає `409`.

Якщо залишку недостатньо — повертається `400`.

Уся операція знаходиться у `transaction.atomic()`. Якщо друге UPDATE не
спрацювало або виникла помилка стану, транзакція відкотить перше UPDATE.

## 8. Скасування заявки

Запит:

```text
POST /api/v1/parking-requests/<id>/cancel/
Authorization: Bearer <access>
```

Скасування має два різні варіанти.

### Скасування draft-заявки

Якщо заявка має стан `draft`:

1. залишок не змінюється;
2. стан змінюється на `cancelled`.

Це не повертає місця, бо вони ще не були зайняті.

### Скасування confirmed-заявки

Якщо заявка має стан `confirmed`:

1. кількість додається назад до `available`;
2. стан змінюється на `cancelled`.

Приклад:

```python
ParkingLevel.objects.filter(
    pk=parking_request.level_id
).update(
    available=F("available") + parking_request.quantity
)
```

Повторний `cancel` повертає `409`. Залишок не повертається вдруге.

Скасування чужої заявки повертає `403` або `404`.

## 9. Права доступу

[api/permissions.py](C:/Users/User/Desktop/starter/api/permissions.py)
містить два класи прав.

### ReadOnlyCatalogPermission

Дозволяє користувачу тільки безпечні методи для каталогу:

- `GET`;
- `HEAD`;
- `OPTIONS`.

Зміна каталогу через API не дозволена класу користувача.

Код перевіряє метод запиту:

```python
request.method in permissions.SAFE_METHODS
```

### IsParkingRequestOwner

Перевіряє автентифікацію:

```python
request.user.is_authenticated
```

Для конкретного об’єкта перевіряє:

```python
obj.owner_id == request.user.id
```

Окремо `get_queryset()` фільтрує список заявок поточного користувача.

Це важливо, бо `has_object_permission()` не викликається для списку.

## 10. Моделі та база даних

[api/models.py](C:/Users/User/Desktop/starter/api/models.py) описує таблиці.

### ParkingLevel

Поля:

- `id`: первинний ключ;
- `name`: унікальна назва до 50 символів;
- `available`: невід’ємна кількість місць.

Обмеження:

```python
models.CheckConstraint(
    condition=Q(available__gte=0),
    name="parking_level_available_nonnegative",
)
```

Це страхувальна перевірка бази. Головний захист гонок все одно жорсткий
SQL-UPDATE у сервісі, бо перевірку Python перед записом не можна назвати безпечною.

### ParkingRequest

Поля:

- `owner`: зв’язок із користувачем, видалення користувача видаляє його заявки;
- `level`: зв’язок із рівнем, видалення рівня захищено `PROTECT`;
- `quantity`: кількість місць від 1;
- `status`: тільки `draft`, `confirmed`, `cancelled`.

Поле кількості перевіряється валідатором і `CheckConstraint`:

```python
condition=Q(quantity__gte=1)
```

Міграції знаходяться у `api/migrations/`.

`0001_initial.py` створює початкові моделі.

Наступні міграції узгоджують довжину назви, валідатори і сортування.

## 11. Серіалізатори

[api/serializers.py](C:/Users/User/Desktop/starter/api/serializers.py)
перетворює Django-моделі в JSON і перевіряє тіла запитів.

`ParkingLevelSerializer` містить лише:

- `id`;
- `name`;
- `available`.

Усі поля read-only.

`ParkingRequestSerializer` містить:

- `id`;
- `owner`;
- `level`;
- `quantity`;
- `status`.

Read-only поля:

- `id`;
- `owner`;
- `status`.

Користувач не може змінити власника або стан у тілі запиту.

## 12. Seed і тестові акаунти

[api/management/commands/seed_attack.py](C:/Users/User/Desktop/starter/api/management/commands/seed_attack.py)
створює:

```text
attacker1 / attack-pass-1
attacker2 / attack-pass-2
```

Акаунти не стають staff або superuser.

Команда видаляє заявки attacker-акаунтів і відновлює рівні:

| ID | Назва | Залишок |
|---|---|---|
| 1 | Рівень -1 | 50 |
| 2 | Рівень 0 | 50 |
| 3 | Рівень 1 | 50 |
| 4 | Рівень 2 | 1 |

Рівень 4 є `race_item` у [contract.json](C:/Users/User/Desktop/starter/contract.json).

Команда ідемпотентна: повторний запуск відновлює початковий стан, бо для
кожного рівня використовується `update_or_create()`.

Запуск:

```powershell
python manage.py seed_attack
```

Після гонок рівень 4 може повернутися до 0. Repeat seed повертає його до 1.

## 13. Коди відповіді

| Код | Значення у цьому API |
|---|---|
| `200` | Операція успішно виконана |
| `201` | Заявка успішно створена |
| `400` | Невалідне тіло або недостатньо місць |
| `401` | Немає токена або токен невірний |
| `403` | Токен є, але користувач не має права |
| `404` | Об’єкт відсутній або він чужий |
| `409` | Перехід стану заборонений або об’єкт не можна видалити |
| `500` | Серверна внутрішня помилка; для атаки це пробій |

Помилку `500` не можна маскувати загальною успішною відповіддю.

Очікувана помилка має перетворюватися у зрозумілий JSON-код:

```json
{"detail": "Недозволений перехід стану заявки."}
```

## 14. Перевірка у повсякденних curl-запитах

Збережіть токен у змінну PowerShell:

```powershell
$response = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/auth/token/" `
  -ContentType "application/json" `
  -Body '{"username":"attacker1","password":"attack-pass-1"}'

$token = $response.access
```

Подивитися каталог:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/levels/"
```

Створити заявку:

```powershell
$body = '{"level":4,"quantity":1}'

$request = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/parking-requests/" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body $body

$request
```

Підтвердити заявку:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/parking-requests/$($request.id)/confirm/" `
  -Headers @{ Authorization = "Bearer $token" }
```

Повторно підтвердити:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/parking-requests/$($request.id)/confirm/" `
  -Headers @{ Authorization = "Bearer $token" }
```

Очікується помилка `409`.

Скасувати:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/parking-requests/$($request.id)/cancel/" `
  -Headers @{ Authorization = "Bearer $token" }
```

Перевірити залишок рівня:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/levels/4/"
```

## 15. Відкрита карта атаки

Скрипт [tools/attack_open.py](C:/Users/User/Desktop/starter/tools/attack_open.py)
перевіряє рядки 1–22.

Повний запуск:

```powershell
python tools\attack_open.py
```

Контрольна точка Етапу 1:

```powershell
python tools\attack_open.py --only 1,2,3,7,8,18,19
```

Перевірки включають:

1. каталог доступний без токена;
2. список заявок без токена не доступний;
3. створення заявки без токена не доступне;
4. каталог відомий без аутентифікації;
5. чужі заявки приховані;
6. підміна `owner` і `status` не спрацьовує;
7. від’ємна або нульова кількість не приймається;
8. неіснуючий рівень не приймається;
9. повторний confirm повертає `409`;
10. повторний cancel повертає `409`;
11. залишок повертається рівно один раз.

Користувач бачить у результаті очікуваний і отриманий код.

Зелений рядок означає, що конкретна перевірка пройшла зараз.

Один зелений прогін не доводить, що гонка повністю захищена.

## 16. Гонки

[tools/race.py](C:/Users/User/Desktop/starter/tools/race.py)
запускає одночасні HTTP-запити.

Для гонки на одній заявці:

```powershell
python tools\race.py --item 4 --orders 10 --same
```

Для різних заявок на одному рівні:

```powershell
python tools\race.py --item 4 --orders 10
```

Для одночасного cancel однієї підтвердженої заявки:

```powershell
python tools\race.py --item 4 --orders 10 --same --action cancel
```

Скрипт:

- отримує токен;
- створює одну або декілька заявок;
- записує залишок до залпу;
- запускає запити через `threading.Barrier`;
- одночасно відпускає всі потоки;
- порівнює коди і залишок.

Гонка має мати рівно одну успішну заявку, якщо бореться 10 запитів за один
remaining spot.

Жодна відповідь не має бути `5xx`.

Після гонки відновіть тестові дані:

```powershell
python manage.py seed_attack
```

## 17. Детальна логіка захисту гонки

Простий код у Python не захищає:

```python
if level.available >= quantity:
    level.available -= quantity
    level.save()
```

Причина: два запити можуть прочитати одне значення до запису.

Безпечний шлях у цьому проєкті:

1. `transaction.atomic()` блокує область логічних змін;
2. заявка читається через `select_for_update()`;
3. залишок перевіряється через `UPDATE` із `available__gte=quantity`;
4. результат `UPDATE` перевіряється;
5. стан заявки перевіряється повторно умовним `UPDATE`;
6. якщо кроку не вдалося виконатися, транзакція відкочується.

Це захищає від одночасних підтверджень однієї заявки та перевищення залишку.

`transaction_mode = "IMMEDIATE"` у SQLite також зменшує ймовірність миттєвої
помилки запису під одночасними запитами.

## 18. Коли треба пояснювати на демо

Коротка схема відповіді для студента:

### Що це за проєкт?

«Це API для бронювання місць на рівні паркінгу».

### Який обмежений ресурс?

«Поле `available` рівня. Воно показує кількість вільних місць».

### Як створюється заявка?

«Користувач передає рівень і кількість. Власник береться із JWT-сесії,
стан завжди `draft`, а залишок не змінюється».

### Як підтверджується заявка?

«Сервіс перевіряє стан і власника, атомарно списує залишок і переводить заявку
в `confirmed`».

### Як скасовується заявка?

«Draft просто переходить у `cancelled`. Confirmed повертає місця і потім переходить
у `cancelled`».

### Як захищено від гонки?

«Не локальною перевіркою в Python, а умовним UPDATE у базі всередині
`transaction.atomic()`. Рядок заявки блоковано, а зміну стану перевіряє база».

### Як захищено чужі заявки?

«Список фільтрується за поточним користувачем, а конкретна заявка перевіряється
через `has_object_permission()`».

### Які помилки очікуються?

«Повторний confirm/cancel — `409`, недостатньо місць — `400`, чужа або
відсутня заявка — `403/404`, без JWT — `401», а `500` вважається пробоєм».

## 19. Перевірки перед демо

Запустити:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test api.tests.test_services
python manage.py seed_attack
python manage.py runserver 127.0.0.1:8000
```

У другому вікні:

```powershell
python tools\attack_open.py --only 1,2,3,7,8,18,19
python tools\attack_open.py --only 11,12,13,14,15,16,17,20
python tools\attack_open.py --only 21,22
python tools\race.py --item 4 --orders 10 --same
python tools\race.py --item 4 --orders 10
```

Перед повторною перевіркою рівня 4 запустіть:

```powershell
python manage.py seed_attack
```

## 20. Безпека і продакшен-нагадування

Це хакатонова конфігурація. Перед реальним продакшеном треба змінити:

- `SECRET_KEY`;
- `DEBUG=False`;
- список `ALLOWED_HOSTS`;
- час життя JWT;
- SQLite на базу для реального паралельного навантаження;
- пароль seed-акаунтів;
- налаштування HTTPS;
- throttling і логування;
- права адмінки.
