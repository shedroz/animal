import telebot
import mysql.connector
import requests
import time
import json
from geopy.distance import geodesic as GD
from telebot import types

TOKEN = "8008521419:AAHyV35DzsUnZjygguIF1BuPNl-awbok0pg"
URL = "https://api.telegram.org/bot"

mydb = mysql.connector.connect(
    host="localhost", user="root", password="January27!", database="shelters_spb"
)

mycursor = mydb.cursor()

# Выполнение SQL-запроса для извлечения данных
mycursor.execute("SELECT title, lon, lat, image_path, street, house, body, work_time FROM shelters")

# Получение всех строк результата
result = mycursor.fetchall()

# Преобразование результата в список кортежей
list_shelters = [(name, lon, lat, image_path, street, house, body, work_time) for name, lon, lat, image_path, street, house, body, work_time in result]

# Закрытие курсора и соединения
mycursor.close()
mydb.close()

# Словарь для хранения состояния пользователей
user_state = {}


def distance_calculation(start_coord):
    list_dist = []
    for shelter in list_shelters:
        dist = GD(start_coord, (shelter[1], shelter[2])).km
        list_dist.append(dist)
    return list_dist


def send_photo(chat_id, photo_path, caption=None, reply_markup=None):
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        requests.post(f"{URL}{TOKEN}/sendPhoto", files=files, data=data)


def get_updates(offset=0):
    result = requests.get(f"{URL}{TOKEN}/getUpdates?offset={offset}").json()
    return result["result"]


def reply_keyboard(chat_id, text):
    reply_markup = {
        "keyboard": [
            [{"request_location": True, "text": "Моя геопозиция"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }
    data = {"chat_id": chat_id, "text": text, "reply_markup": json.dumps(reply_markup)}
    requests.post(f"{URL}{TOKEN}/sendMessage", data=data)


def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{URL}{TOKEN}/sendMessage", data=data)


def check_message(chat_id, message):
    if message.lower() == "/start":
        welcome_message = (
            "Привет! 🐾\n\n"
            "Я — твой помощник в поиске ближайшего приюта для животных. "
            "Просто отправь мне свою геопозицию, и я найду приют, который находится ближе всего к тебе. "
            "Там ты сможешь найти пушистых друзей, которые ждут своего хозяина!"
        )
        send_message(chat_id, welcome_message)
    else:
        send_message(chat_id, "Я не понимаю тебя :(")


def geocoder(latitude, longitude):
    token = "pk.b992831a2ca7e1437589d71ddaeadfd4"
    headers = {"Accept-Language": "ru"}
    response = requests.get(
        f"https://eu1.locationiq.com/v1/reverse.php?key={token}&lat={latitude}&lon={longitude}&format=json",
        headers=headers,
    )

    if response.status_code == 200:
        address = response.json()

        street = address.get("address", {}).get("road", "")
        house_number = address.get("address", {}).get("house_number", "")

        latitude = round(float(address.get("lat", 0)), 6)
        longitude = round(float(address.get("lon", 0)), 6)
    else:
        return "Ошибка при обращении к API."


def format_address(street, house, body):
    address = f"{street}, {house}"
    if body and body != "0":
        address += f", корпус {body}"
    return address


def show_shelter(chat_id, shelter_index):
    sorted_shelters = user_state[chat_id]["sorted_shelters"]
    shelter = sorted_shelters[shelter_index]
    distance = GD(user_state[chat_id]["user_coord"], (shelter[1], shelter[2])).km

    # Формируем адрес
    address = format_address(shelter[4], shelter[5], shelter[6])

    # Формируем текстовый ответ
    response = (
        f"Приют: {shelter[0]}\n"
        f"Адрес: {address}\n"
        f"Время работы: {shelter[7]}\n"
        f"Расстояние до него: {round(distance, 2)} км."
    )

    # Создаем инлайн-кнопку "Следующий приют"
    if shelter_index + 1 < len(sorted_shelters):
        reply_markup = {
            "inline_keyboard": [[{"text": "Следующий приют", "callback_data": "next_shelter"}]]
        }
    else:
        reply_markup = None

    # Отправляем изображение приюта
    if shelter[3]:  # Проверяем, есть ли путь к изображению
        try:
            send_photo(
                chat_id,
                shelter[3],
                caption=response,
                reply_markup=reply_markup,
            )
        except FileNotFoundError:
            send_message(
                chat_id,
                "Изображение приюта не найдено.",
                reply_markup=reply_markup,
            )
    else:
        send_message(chat_id, response, reply_markup=reply_markup)


def run():
    update_id = get_updates()[-1]["update_id"] if get_updates() else 0
    while True:
        time.sleep(2)
        messages = get_updates(update_id)
        for message in messages:
            if update_id < message["update_id"]:
                update_id = message["update_id"]

                # Обработка текстовых сообщений
                if "message" in message and "text" in message["message"]:
                    chat_id = message["message"]["chat"]["id"]
                    user_message = message["message"]["text"]
                    check_message(chat_id, user_message)

                # Обработка геопозиции
                elif "message" in message and "location" in message["message"]:
                    chat_id = message["message"]["chat"]["id"]
                    latitude = message["message"]["location"]["latitude"]
                    longitude = message["message"]["location"]["longitude"]
                    user_coord = (latitude, longitude)

                    # Рассчитываем расстояния до всех приютов
                    distances = distance_calculation(user_coord)

                    # Сортируем приюты по расстоянию
                    sorted_shelters = sorted(list_shelters, key=lambda x: GD(user_coord, (x[1], x[2])).km)

                    # Сохраняем состояние пользователя
                    user_state[chat_id] = {
                        "sorted_shelters": sorted_shelters,
                        "current_index": 0,
                        "user_coord": user_coord,
                    }

                    # Показываем ближайший приют
                    show_shelter(chat_id, 0)

                # Обработка нажатия на инлайн-кнопку
                elif "callback_query" in message:
                    callback_query = message["callback_query"]
                    chat_id = callback_query["message"]["chat"]["id"]
                    if callback_query["data"] == "next_shelter":
                        if chat_id in user_state:
                            next_shelter_index = user_state[chat_id]["current_index"] + 1
                            if next_shelter_index < len(user_state[chat_id]["sorted_shelters"]):
                                user_state[chat_id]["current_index"] = next_shelter_index
                                show_shelter(chat_id, next_shelter_index)
                            else:
                                send_message(chat_id, "Это был последний приют в списке.")
                        else:
                            send_message(chat_id, "Сначала отправьте свою геопозицию.")


if __name__ == "__main__":
    run()