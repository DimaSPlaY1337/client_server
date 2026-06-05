from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import hashlib
import os

app = Flask(__name__)
# Секретный ключ необходим для безопасной работы сессий во Flask
app.secret_key = 'super_secret_key_change_me' 

# Укажите корректный путь к вашей БД (согласно вашей структуре)
DB_PATH = 'db.sqlite' 

def verify_user(username, password):
    """Функция проверки пользователя в БД"""
    # Хешируем введенный пароль, так как в БД он, скорее всего, хранится в sha256
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    if not os.path.exists(DB_PATH):
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Если пароли хранятся в открытом виде, замените hashed_password на password
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = cursor.fetchone()
    conn.close()
    
    return user is not None

@app.route("/", methods=["GET", "POST"])
def login():
    message = ""
    # Если пользователь уже авторизован, сразу кидаем в админку
    if session.get('is_logged'):
        return redirect(url_for('admin_panel'))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if verify_user(username, password):
            session['is_logged'] = True
            session['username'] = username
            return redirect(url_for('admin_panel'))
        else:
            message = "Неверный логин или пароль!"
            
    # Рендерим шаблон. Убедитесь, что mainpage.html лежит в папке templates/
    return render_template('mainpage.html', title='Вход', is_logged=False, message=message, heading="Авторизация")

@app.route("/admin")
def admin_panel():
    if not session.get('is_logged'):
        return redirect(url_for('login'))
    return render_template('mainpage.html', title='Админка', is_logged=True, message=f"Добро пожаловать, {session['username']}!", heading="Панель администратора")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Запуск на всех интерфейсах (полезно для Docker)
    app.run(host='0.0.0.0', port=5000)