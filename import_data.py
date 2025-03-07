import pandas as pd
import mysql.connector

# Подключение к MySQL
mydb = mysql.connector.connect(
    host="localhost", user="root", password="January27!", database="shelters_spb"
)
mycursor = mydb.cursor()

# Чтение данных из Excel
excel_file = r"C:\Users\Анастасия Дроздова\OneDrive\Рабочий стол\Приюты.xlsx"
df = pd.read_excel(excel_file, usecols=["animal_id", "image_path"])

# SQL-запрос для обновления данных
sql = "UPDATE animals SET image_path = %s WHERE animal_id = %s"

# Преобразование данных в список кортежей
data = [(row["image_path"], row["animal_id"]) for _, row in df.iterrows()]

# Обновление данных
try:
    mycursor.executemany(sql, data)
    mydb.commit()
    print(f"Обновлено {mycursor.rowcount} строк.")
except mysql.connector.Error as err:
    print(f"Ошибка: {err}")