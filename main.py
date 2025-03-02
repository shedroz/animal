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

# Выполнение SQL-запроса для извлечения lon и lat
mycursor.execute("SELECT lon, lat FROM shelters")

# Получение всех строк результата
result = mycursor.fetchall()

# Преобразование результата в список кортежей
list_border_coord = [(lon, lat) for lon, lat in result]

# Закрытие курсора и соединения
mycursor.close()
mydb.close()

# Вывод результата
print(list_border_coord)


def distance_calculation(start_coord):
    list_dist = []
    for bord_coord in list_border_coord:

        # Для расчета расстояния используем функцию GD([1 координаты точки],[2 координаты точки].[единица измерения расстояния])
        dist = GD(start_coord, bord_coord).km

        # Добовляем в список результат
        list_dist.append(dist)

    # Возвращаем минимальную дистанцию из списка
    return min(list_dist)


# mycursor.execute("SELECT * FROM shelters")
# myresult = mycursor.fetchone()

# print(myresult)


def get_updates(offset=0):
    result = requests.get(f"{URL}{TOKEN}/getUpdates?offset={offset}").json()
    return result["result"]


def reply_keyboard(chat_id, text):
    reply_markup = {
        "keyboard": [
            ["Привет", "Hello"],
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
    if message.lower() in ["привет", "hello"]:
        send_message(chat_id, "Привет :)")
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

        if street and house_number:
            return f"Твое местоположение: {street}, {house_number}"
        elif street:
            return f"Улица: {street}"
        elif house_number:
            return f"Дом: {house_number}"
        else:
            return "Улица и дом не найдены."
    else:
        return "Ошибка при обращении к API."


def run():
    update_id = get_updates()[-1][
        "update_id"
    ]  # Присваиваем ID последнего отправленного сообщения боту
    while True:
        time.sleep(2)
        messages = get_updates(update_id)  # Получаем обновления
        for message in messages:
            # Если в обновлении есть ID больше чем ID последнего сообщения, значит пришло новое сообщение
            if update_id < message["update_id"]:
                update_id = message[
                    "update_id"
                ]  # Присваиваем ID последнего отправленного сообщения боту
                if user_message := message["message"].get(
                    "text"
                ):  # Проверим, есть ли текст в сообщении
                    check_message(
                        message["message"]["chat"]["id"], user_message
                    )  # Отвечаем
                if user_location := message["message"].get(
                    "location"
                ):  # Проверим, если ли location в сообщении
                    latitude = user_location["latitude"]
                    longitude = user_location["longitude"]
                    send_message(
                        message["message"]["chat"]["id"], geocoder(latitude, longitude)
                    )


if __name__ == "__main__":
    run()
