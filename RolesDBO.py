from DBO import DBO
from datetime import datetime

class RolesDBO(DBO):
    def __init__(self, connection):
        super().__init__(connection)
        self.attributes = dict()
        self.attributes['table_name'] = 'ROLES'
        self.id = None
        self.name = None
        self.author = None
        self.created = None
        self.last_editor = None
        self.last_change = None
        self.change_cnt = 0

    def dbInsert(self):
        self.created = datetime.now().isoformat()
        self.last_change = self.created
        self.change_cnt = 0
        self.author = 'SYSTEM'
        self.last_editor = 'SYSTEM'

        query = "INSERT INTO roles (id, name, author, created, last_editor, last_change, change_cnt) VALUES (?, ?, ?, ?, ?, ?, ?)"
        values = (self.id, self.name, self.author, self.created, self.last_editor, self.last_change, self.change_cnt)
        cursor = self.db.cursor()
        cursor.execute(query, values)
        self.db.commit()

    def dbUpdate(self):
        cursor = self.db.cursor()
        try:
            # Кидаем текущее состояние в историческую таблицу
            h_query = "INSERT INTO roles_H (id, name, author, created, last_editor, last_change, change_cnt) VALUES (?, ?, ?, ?, ?, ?, ?)"
            h_values = (self.id, self.name, self.author, self.created, self.last_editor, self.last_change, self.change_cnt)
            cursor.execute(h_query, h_values)

            # Обновляем метаданные
            self.change_cnt += 1
            self.last_change = datetime.now().isoformat()
            self.last_editor = 'SYSTEM'

            u_query = "UPDATE roles SET name=?, author=?, created=?, last_editor=?, last_change=?, change_cnt=? WHERE id=?"
            u_values = (self.name, self.author, self.created, self.last_editor, self.last_change, self.change_cnt, self.id)
            cursor.execute(u_query, u_values)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f'Update failed: {e}')

    def dbDelete(self):
        cursor = self.db.cursor()
        try:
            # Сохраняем удаленную запись в D-таблицу перед сносом
            d_query = "INSERT INTO roles_D (id, name, author, created, last_editor, last_change, change_cnt) VALUES (?, ?, ?, ?, ?, ?, ?)"
            d_values = (self.id, self.name, self.author, self.created, self.last_editor, self.last_change, self.change_cnt)
            cursor.execute(d_query, d_values)

            cursor.execute("DELETE FROM roles WHERE id=?", (self.id,))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f'Delete failed: {e}')
