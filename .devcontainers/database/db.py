import sqlite3

class Database:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.cursor = self.connection.cursor()

    def __del__(self):
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

    def create_database(self, schema: dict):
        # Перебираем список таблиц. Каждый элемент списка - это словарь вида {'users': {...}}
        for table_item in schema['database']['tables']:
            # Получаем имя таблицы (первый ключ словаря)
            table_name = list(table_item.keys())[0]
            table_data = table_item[table_name]

            # Ищем поля (учитываем возможную опечатку 'fileds' в конфиге)
            fields_data = table_data.get('fields') or table_data.get('fileds')
            
            if not fields_data:
                print(f"Внимание: у таблицы {table_name} нет полей, пропускаем.")
                continue

            columns_sql = []
            
            # Перебираем поля. В вашем YAML это словарь: key=имя_поля, value=строка_параметров
            for col_name, col_params in fields_data.items():
                # Очищаем параметры для совместимости с SQLite
                clean_params = col_params
                
                # Замены для вашего синтаксиса:
                # 1. NOT_NULL -> NOT NULL
                clean_params = clean_params.replace('NOT_NULL', 'NOT NULL')
                # 2. FOREIGN_KEY -> REFERENCES (для inline ключей)
                clean_params = clean_params.replace('FOREIGN_KEY', 'REFERENCES')
                # 3. Добавляем KEY к PRIMARY, если его нет (чтобы PRIMARY AUTOINCREMENT заработал)
                if 'PRIMARY' in clean_params and 'PRIMARY KEY' not in clean_params:
                    clean_params = clean_params.replace('PRIMARY', 'PRIMARY KEY')
                
                # Склеиваем имя и параметры: "id INTEGER PRIMARY KEY AUTOINCREMENT"
                columns_sql.append(f"{col_name} {clean_params}")

            # Собираем финальный запрос
            columns_str = ", ".join(columns_sql)
            sql_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str});"

            try:
                self.cursor.execute(sql_query)
                # print(f"Таблица '{table_name}' проверена/создана.")
            except sqlite3.Error as e:
                print(f"Ошибка при создании таблицы '{table_name}':\nЗапрос: {sql_query}\nОшибка: {e}")

        self.connection.commit()