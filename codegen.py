import yaml
import os

def run_codegen():
    config_path = '.devcontainers/config.yaml'
    
    if not os.path.exists(config_path):
        print("Конфиг не найден")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        schema = yaml.safe_load(f)

    tables = schema['database']['tables']
    # Служебные поля, которые мы добавляли в базу
    extra_fields = ["author", "created", "last_editor", "last_change", "change_cnt"]

    # 1. Генерируем базовый DBO.py
    with open('DBO.py', 'w', encoding='utf-8') as f:
        f.write("class DBO:\n")
        f.write("    def __init__(self, connection):\n")
        f.write("        self.db = connection\n")

    # 2. Бежим по таблицам и генерим классы
    for table_entry in tables:
        for table_name, table_data in table_entry.items():
            class_name = table_name.capitalize() + "DBO"
            filename = class_name + ".py"
            
            # Собираем все поля (основные + аудит)
            fields = list(table_data['fields'].keys())
            all_fields = fields + extra_fields
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("from DBO import DBO\n")
                f.write("from datetime import datetime\n\n")
                
                f.write(f"class {class_name}(DBO):\n")
                f.write("    def __init__(self, connection):\n")
                f.write("        super().__init__(connection)\n")
                f.write("        self.attributes = dict()\n")
                f.write(f"        self.attributes['table_name'] = '{table_name.upper()}'\n")
                
                # Инициализация всех полей
                for field in all_fields:
                    if field == 'change_cnt':
                        f.write(f"        self.{field} = 0\n")
                    else:
                        f.write(f"        self.{field} = None\n")
                
                cols = ", ".join(all_fields)
                placements = ", ".join(["?"] * len(all_fields))
                
                # --- Метод dbInsert ---
                f.write("\n    def dbInsert(self):\n")
                f.write("        self.created = datetime.now().isoformat()\n")
                f.write("        self.last_change = self.created\n")
                f.write("        self.change_cnt = 0\n")
                f.write("        self.author = 'SYSTEM'\n")
                f.write("        self.last_editor = 'SYSTEM'\n\n")
                
                f.write(f"        query = \"INSERT INTO {table_name} ({cols}) VALUES ({placements})\"\n")
                f.write(f"        values = ({', '.join(['self.' + f for f in all_fields])})\n")
                f.write("        cursor = self.db.cursor()\n")
                f.write("        cursor.execute(query, values)\n")
                f.write("        self.db.commit()\n")
                
                # --- Метод dbUpdate ---
                f.write("\n    def dbUpdate(self):\n")
                f.write("        cursor = self.db.cursor()\n")
                f.write("        try:\n")
                f.write("            # Кидаем текущее состояние в историческую таблицу\n")
                f.write(f"            h_query = \"INSERT INTO {table_name}_H ({cols}) VALUES ({placements})\"\n")
                f.write(f"            h_values = ({', '.join(['self.' + f for f in all_fields])})\n")
                f.write("            cursor.execute(h_query, h_values)\n\n")
                
                f.write("            # Обновляем метаданные\n")
                f.write("            self.change_cnt += 1\n")
                f.write("            self.last_change = datetime.now().isoformat()\n")
                f.write("            self.last_editor = 'SYSTEM'\n\n")
                
                # При апдейте обновляем всё, кроме ID
                update_cols = [f for f in all_fields if f != 'id']
                set_clause = ", ".join([f"{c}=?" for c in update_cols])
                u_values = ", ".join(["self." + c for c in update_cols]) + ", self.id"
                
                f.write(f"            u_query = \"UPDATE {table_name} SET {set_clause} WHERE id=?\"\n")
                f.write(f"            u_values = ({u_values})\n")
                f.write("            cursor.execute(u_query, u_values)\n")
                f.write("            self.db.commit()\n")
                f.write("        except Exception as e:\n")
                f.write("            self.db.rollback()\n")
                f.write("            print(f'Update failed: {e}')\n")
                
                # --- Метод dbDelete ---
                f.write("\n    def dbDelete(self):\n")
                f.write("        cursor = self.db.cursor()\n")
                f.write("        try:\n")
                f.write("            # Сохраняем удаленную запись в D-таблицу перед сносом\n")
                f.write(f"            d_query = \"INSERT INTO {table_name}_D ({cols}) VALUES ({placements})\"\n")
                f.write(f"            d_values = ({', '.join(['self.' + f for f in all_fields])})\n")
                f.write("            cursor.execute(d_query, d_values)\n\n")
                
                f.write(f"            cursor.execute(\"DELETE FROM {table_name} WHERE id=?\", (self.id,))\n")
                f.write("            self.db.commit()\n")
                f.write("        except Exception as e:\n")
                f.write("            self.db.rollback()\n")
                f.write("            print(f'Delete failed: {e}')\n")

if __name__ == '__main__':
    run_codegen()
    print("Генерация завершена. Классы DBO созданы.")