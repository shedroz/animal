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

# Выполнение SQL-запроса для извлечения name, lon и lat
mycursor.execute("SELECT title, lon, lat, image_path FROM shelters")

# Получение всех строк результата
result = mycursor.fetchall()

# Преобразование результата в список кортежей (name, lon, lat)
list_shelters = [(name, lon, lat, image_path) for name, lon, lat, image_path in result]

# Закрытие курсора и соединения
mycursor.close()
mydb.close()


def distance_calculation(start_coord):
    list_dist = []
    for shelter in list_shelters:
        # Для расчета расстояния используем функцию GD([1 координаты точки],[2 координаты точки].[единица измерения расстояния])
        dist = GD(start_coord, (shelter[1], shelter[2])).km
        # Добавляем в список результат
        list_dist.append(dist)
    # Возвращаем минимальную дистанцию из списка
    return min(list_dist)


def send_photo(chat_id, photo_path, caption=None):
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        requests.post(f"{URL}{TOKEN}/sendPhoto", files=files, data=data)


def get_updates(offset=0):
    result = requests.get(f"{URL}{TOKEN}/getUpdates?offset={offset}").json()
    return result["result"]


def reply_keyboard(chat_id, text):
    reply_markup = {
        "keyboard": [
            [{"request_location": True, "text": "Где я нахожусь"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }
    data = {"chat_id": chat_id, "text": text, "reply_markup": json.dumps(reply_markup)}
    requests.post(f"{URL}{TOKEN}/sendMessage", data=data)


def send_message(chat_id, text):
    requests.get(f"{URL}{TOKEN}/sendMessage?chat_id={chat_id}&text={text}")


def check_message(chat_id, message):
    if message.lower() == "/start":
        welcome_message = (
            "Привет! 🐾\n\n"
            "Я — твой помощник в поиске ближайшего приюта для животных. "
            "Просто отправь мне свою геопозицию, и я найду приют, который находится ближе всего к тебе. "
            "Там ты сможешь найти пушистых друзей, которые ждут своего хозяина!"
        )
        send_message(chat_id, welcome_message)
        reply_keyboard(chat_id, "Отправь свою геопозицию, чтобы найти ближайший приют.")
    else:
        reply_keyboard(chat_id, "Я не понимаю тебя :(")


def geocoder(latitude, longitude):
    token = "pk.b992831a2ca7e1437589d71ddaeadfd4"
    headers = {"Accept-Language": "ru"}
    response = requests.get(
        f"https://eu1.locationiq.com/v1/reverse.php?key={token}&lat={latitude}&lon={longitude}&format=json",
        headers=headers,
    )

    if response.status_code == 200:
        address = response.json()

        # Извлекаем улицу и номер дома
        street = address.get("address", {}).get("road", "")
        house_number = address.get("address", {}).get("house_number", "")

        # Извлекаем долготу и широту
        latitude = round(float(address.get("lat", 0)), 6)
        longitude = round(float(address.get("lon", 0)), 6)

        if street and house_number:
            return f"Твое местоположение: {street}, {house_number}. Широта: {latitude}, Долгота: {longitude}"
        elif street:
            return f"Улица: {street}. Широта: {latitude}, Долгота: {longitude}"
        elif house_number:
            return f"Дом: {house_number}. Широта: {latitude}, Долгота: {longitude}"
        else:
            return "Улица и дом не найдены."
    else:
        return "Ошибка при обращении к API."


def find_nearest_shelter(user_coord):
    min_distance = float("inf")
    nearest_shelter = None

    for shelter in list_shelters:
        distance = GD(user_coord, (shelter[1], shelter[2])).km
        if distance < min_distance:
            min_distance = distance
            nearest_shelter = shelter

    return nearest_shelter, min_distance


def run():
    update_id = get_updates()[-1]["update_id"]
    while True:
        time.sleep(2)
        messages = get_updates(update_id)
        for message in messages:
            if update_id < message["update_id"]:
                update_id = message["update_id"]
                if user_message := message["message"].get("text"):
                    check_message(message["message"]["chat"]["id"], user_message)
                if user_location := message["message"].get("location"):
                    latitude = user_location["latitude"]
                    longitude = user_location["longitude"]
                    user_coord = (latitude, longitude)

                    # Находим ближайший приют и расстояние до него
                    nearest_shelter, distance = find_nearest_shelter(user_coord)

                    # Формируем текстовый ответ
                    response = (
                        f"Ближайший приют: {nearest_shelter[0]}\n"
                        f"Координаты: {nearest_shelter[1]}, {nearest_shelter[2]}\n"
                        f"Расстояние до него: {round(distance, 2)} км."
                    )

                    # Отправляем изображение приюта
                    if nearest_shelter[3]:  # Проверяем, есть ли путь к изображению
                        try:
                            send_photo(
                                message["message"]["chat"]["id"],
                                nearest_shelter[3],
                                caption=response,
                            )
                        except FileNotFoundError:
                            send_message(
                                message["message"]["chat"]["id"],
                                "Изображение приюта не найдено.",
                            )
                    else:
                        send_message(message["message"]["chat"]["id"], response)


if __name__ == "__main__":
    run()
