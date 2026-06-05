# #!/usr/bin/env python3
# import argparse
# import os
# import yaml

# if __name__=="__main__":
#     parser=argparse.ArgumentParser(prog="___")
#     parser.add_argument('-db', '--database', type=str, default='db.sqlite')
#     parser.add_argument('-s', '--shema', type=str, required=False, default='config.yaml', help="Path to schema")
#     args=parser.parse_args()

# class FileNotExists(Exception):
#     pass

# if not os.path.exists(args.shema) or not os.path.isfile(args.shema): 
#     raise FileNotExists

# from database.db import Database
# with open(args.shema, 'r', encoding="utf-8") as f:
#     shema = yaml.safe_load(f)
# db = Database(args.databse)
# db.create_databse(shema)
# print("БД создана")
#!/usr/bin/env python3
import argparse
import os
import yaml
import sys # Для корректного выхода из программы

# Сначала все импорты
# (Убедитесь, что папка database/db.py существует и в ней есть класс Database)
try:
    from database.db import Database
except ImportError:
    print("Ошибка: Не найден модуль database.db")
    sys.exit(1)

class FileNotExists(Exception):
    """Исключение для несуществующего файла"""
    pass

def main():
    # 1. Парсинг аргументов
    parser = argparse.ArgumentParser(prog="DatabaseInitializer")
    
    # Вычисляем путь к родительской директории
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Папка, где лежит main.py
    parent_dir = os.path.dirname(current_dir)  # Родительская папка
    default_db_path = os.path.join(parent_dir, 'db.sqlite')  # Путь к БД в родительской папке
    # 1. Парсинг аргументов
    parser.add_argument('-db', '--database', type=str, default=default_db_path, help="Path to database file")
    parser.add_argument('-s', '--schema', type=str, required=False, default='config.yaml', help="Path to schema config")
    
    args = parser.parse_args()

    # 2. Проверка файла схемы
    if not os.path.exists(args.schema) or not os.path.isfile(args.schema):
        # Лучше просто вывести ошибку, чем кидать кастомный эксепшн без обработки
        print(f"Ошибка: Файл схемы '{args.schema}' не найден.")
        sys.exit(1)

    # 3. Чтение конфига
    try:
        with open(args.schema, 'r', encoding="utf-8") as f:
            schema_data = yaml.safe_load(f)
    except Exception as e:
        print(f"Ошибка при чтении YAML: {e}")
        sys.exit(1)

    # 4. Работа с БД
    try:
        db = Database(args.database)
        db.create_database(schema_data)
        print(f"БД '{args.database}' успешно обновлена/создана.")
    except Exception as e:
        print(f"Критическая ошибка при работе с БД: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
