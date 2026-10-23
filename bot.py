import os
import telebot
from config import TOKEN

bot = telebot.TeleBot(TOKEN)
FILE = "data/ads.txt"


# ЛР 5.2: класс объявления
class Ad:
    def __init__(self, number, user_id, kind, item, place, contact,
                 status="active", photo_id=""):
        self.number = number
        self.user_id = user_id
        self.kind = kind
        self.item = item
        self.place = place
        self.contact = contact
        self.status = status
        self.photo_id = photo_id

    def show(self):
        return (f"№{self.number} — {self.kind}\n"
                f"Вещь: {self.item}\n"
                f"Место: {self.place}\n"
                f"Контакт: {self.contact}\n"
                f"Статус: {self.status}")


# ЛР 5.1: чтение объявлений из текстового файла
# Старые строки из 7 полей тоже можно прочитать (без фото).
def load_ads():
    result = []
    if not os.path.exists(FILE):
        return result

    with open(FILE, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("|")
            if len(parts) == 7 or len(parts) == 8:
                try:
                    photo_id = parts[7] if len(parts) == 8 else ""
                    ad = Ad(int(parts[0]), int(parts[1]), parts[2],
                            parts[3], parts[4], parts[5], parts[6], photo_id)
                    result.append(ad)
                except ValueError:
                    pass
    return result


# ЛР 5.1: сохранение списка объявлений
# Сохраняем file_id фотографии, а не сам файл изображения.
def save_ads():
    os.makedirs("data", exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as file:
        for ad in ads:
            line = (f"{ad.number}|{ad.user_id}|{ad.kind}|{ad.item}|"
                    f"{ad.place}|{ad.contact}|{ad.status}|{ad.photo_id}\n")
            file.write(line)


ads = load_ads()   # ЛР 3: список объявлений
steps = {}         # ЛР 3: словарь этапов заполнения


def show_ads(chat_id, results):
    if len(results) == 0:
        bot.send_message(chat_id, "Объявлений не найдено.")
        return
    for ad in results:
        bot.send_message(chat_id, ad.show())
        if ad.photo_id:
            try:
                bot.send_photo(chat_id, ad.photo_id)
            except Exception:
                bot.send_message(chat_id, "Не удалось показать фото.")


def start_form(message, kind):
    steps[message.from_user.id] = {"step": "item", "kind": kind}
    bot.send_message(message.chat.id, "Напиши название вещи (например, чёрный рюкзак):")


def finish_ad(message, photo_id=""):
    user_id = message.from_user.id
    state = steps.get(user_id)
    if not state or state["step"] != "photo":
        bot.send_message(message.chat.id, "Сначала создай объявление через /lost или /found.")
        return

    number = ads[-1].number + 1 if ads else 1
    username = message.from_user.username
    contact = "@" + username if username else "не указан"
    ad = Ad(number, user_id, state["kind"], state["item"],
            state["place"], contact, photo_id=photo_id)
    ads.append(ad)
    save_ads()
    steps.pop(user_id, None)
    bot.send_message(message.chat.id, "✅ Объявление добавлено!")
    show_ads(message.chat.id, [ad])
    if not username:
        bot.send_message(message.chat.id, "Для связи с вами укажите username в настройках Telegram.")


@bot.message_handler(commands=["start", "help"])
def start(message):
    steps.pop(message.from_user.id, None)
    bot.send_message(message.chat.id,
        "🏫 CampusFinder — бюро находок\n\n"
        "/lost — я потерял вещь\n"
        "/found — я нашёл вещь\n"
        "/all — все активные объявления\n"
        "/search слово — поиск по вещи или месту\n"
        "/mine — мои объявления\n"
        "/close номер — закрыть своё объявление\n"
        "/skip — пропустить фото\n"
        "/cancel — отменить ввод")


@bot.message_handler(commands=["lost"])
def lost(message):
    start_form(message, "Потерял")


@bot.message_handler(commands=["found"])
def found(message):
    start_form(message, "Нашёл")


@bot.message_handler(commands=["cancel"])
def cancel(message):
    steps.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Ввод отменён. Открой /start.")


@bot.message_handler(commands=["skip"])
def skip(message):
    finish_ad(message)


@bot.message_handler(commands=["all"])
def all_ads(message):
    active = [ad for ad in ads if ad.status == "active"]
    show_ads(message.chat.id, active)


@bot.message_handler(commands=["mine"])
def mine(message):
    my_ads = [ad for ad in ads if ad.user_id == message.from_user.id]
    show_ads(message.chat.id, my_ads)


@bot.message_handler(commands=["search"])
def search(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "Пример: /search рюкзак")
        return

    word = parts[1].strip().lower()
    found_ads = []
    for ad in ads:
        if ad.status == "active" and (word in ad.item.lower() or word in ad.place.lower()):
            found_ads.append(ad)
    show_ads(message.chat.id, found_ads)


@bot.message_handler(commands=["close"])
def close(message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "Пример: /close 2")
        return

    number = int(parts[1])
    for ad in ads:
        if ad.number == number and ad.user_id == message.from_user.id:
            ad.status = "closed"
            save_ads()
            bot.send_message(message.chat.id, "Объявление закрыто.")
            return
    bot.send_message(message.chat.id, "Объявление не найдено или оно не ваше.")


# ЛР 5.1: обработка фото, хранится только Telegram file_id
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    state = steps.get(message.from_user.id)
    if state and state["step"] == "photo":
        finish_ad(message, message.photo[-1].file_id)
    else:
        bot.send_message(message.chat.id, "Сначала введи /lost или /found и заполни название и место.")


# ЛР 2 и 3: обычный текст используется при заполнении объявления
@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.from_user.id
    if user_id not in steps:
        bot.send_message(message.chat.id, "Выбери действие через /start.")
        return

    state = steps[user_id]
    if state["step"] == "photo":
        bot.send_message(message.chat.id, "Теперь пришли фото или введи /skip.")
        return

    text = message.text.strip().replace("|", "/").replace("\n", " ")
    if len(text) < 2 or len(text) > 100:
        bot.send_message(message.chat.id, "Введите от 2 до 100 символов.")
        return

    if state["step"] == "item":
        state["item"] = text
        state["step"] = "place"
        bot.send_message(message.chat.id,
                         "Где потеряли или нашли вещь? (например, библиотека, аудитория 205)")
    elif state["step"] == "place":
        state["place"] = text
        state["step"] = "photo"
        bot.send_message(message.chat.id,
                         "Теперь пришли фотографию вещи или введи /skip, если фото нет.")


print("CampusFinder запущен. Для остановки нажмите Ctrl+C.")
bot.polling(none_stop=True)
