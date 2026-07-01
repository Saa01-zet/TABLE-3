import sqlite3
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this_in_production'  # Секретный ключ для сессий
CORS(app)


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Необходимо авторизоваться'}), 401
        return f(*args, **kwargs)

    return decorated_function


# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn


# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


# Страница регистрации
@app.route('/register')
def register_page():
    return render_template('register.html')


# Страница авторизации
@app.route('/login')
def login_page():
    return render_template('login.html')


# Страница профиля (только для авторизованных)
@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('profile.html')


# Страница редактирования профиля (только для авторизованных)
@app.route('/edit_profile')
def edit_profile_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('edit_profile.html')


# Обработчик регистрации
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not username or not email or not password:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        if len(password) < 6:
            return jsonify({'message': 'Пароль должен содержать не менее 6 символов'}), 400

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user:
            conn.close()
            return jsonify({'message': 'Пользователь уже зарегистрирован'}), 400

        conn.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, password)
        )
        conn.commit()
        conn.close()

        return jsonify({'message': 'Регистрация выполнена успешно'}), 201

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


# Обработчик авторизации
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not email or not password:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if not user:
            return jsonify({'message': 'Неверный email или пароль'}), 401

        if user['password'] != password:
            return jsonify({'message': 'Неверный email или пароль'}), 401

        # Сохраняем данные пользователя в сессии
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['email'] = user['email']

        return jsonify({
            'message': 'Добро пожаловать!',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


# Получение профиля пользователя
@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        user_id = session.get('user_id')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()

        if not user:
            return jsonify({'message': 'Пользователь не найден'}), 404

        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


# Обновление профиля пользователя
@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    try:
        data = request.json
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        user_id = session.get('user_id')

        if not username or not email:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        conn = get_db_connection()

        # Проверяем, не занят ли email другим пользователем
        existing_user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND id != ?',
            (email, user_id)
        ).fetchone()

        if existing_user:
            conn.close()
            return jsonify({'message': 'Этот email уже используется другим пользователем'}), 400

        # Обновляем данные пользователя
        conn.execute(
            'UPDATE users SET username = ?, email = ? WHERE id = ?',
            (username, email, user_id)
        )
        conn.commit()
        conn.close()

        # Обновляем данные в сессии
        session['username'] = username
        session['email'] = email

        return jsonify({
            'message': 'Профиль успешно обновлен',
            'user': {
                'id': user_id,
                'username': username,
                'email': email
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


# Выход из аккаунта
@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'message': 'Вы успешно вышли из аккаунта'}), 200
    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)