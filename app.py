from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

# from app import app, db
import psycopg2

DB_PARAMS = "dbname=taskmanager user=postgres password=password host=localhost"

app = Flask(__name__)

# Настройки базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost/taskmanager'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/taskmanager?client_encoding=WIN1251'



app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Промежуточная таблица
task_assignees = db.Table('task_assignees',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='in progress')

    assignees = db.relationship('User', secondary=task_assignees, backref='tasks')

    def __repr__(self):
        return f'<Task {self.id}: {self.title}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


@app.route('/')
def index():
    tasks = Task.query.all()  # Получаем все задачи из базы данных
    return render_template('index.html', tasks=tasks)

@app.route('/task/<int:task_id>')
def task_page(task_id):
    task = Task.query.get(task_id)
    if not task:
        return render_template('error.html', message="Задача не найдена"), 404
    return render_template('task.html', task=task)

@app.route('/user/<int:user_id>')
def user_page(user_id):
    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message="Пользователь не найден"), 404
    return render_template('user.html', user=user)


@app.route('/task/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    title = data.get('title')
    status = data.get('status')

    if not isinstance(title, str) or not isinstance(status, str):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        conn = psycopg2.connect(DB_PARAMS)
        cur = conn.cursor()

        # Проверяем, существует ли задача
        cur.execute("SELECT id FROM task WHERE id = %s", (task_id,))
        if not cur.fetchone():
            return jsonify({"error": "Task not found"}), 404

        cur.execute("UPDATE task SET title = %s, status = %s WHERE id = %s",
                    (title, status, task_id))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "Task updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        conn = psycopg2.connect(DB_PARAMS)
        cur = conn.cursor()

        # Проверяем, существует ли задача
        cur.execute("SELECT id FROM task WHERE id = %s", (task_id,))
        if not cur.fetchone():
            return jsonify({"error": "Task not found"}), 404

        cur.execute("DELETE FROM task WHERE id = %s", (task_id,))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/task/<int:task_id>/assign', methods=['POST'])
def assign_user_to_task(task_id):
    data = request.json
    user_id = data.get('user_id')

    if not isinstance(user_id, int):
        return jsonify({"error": "Invalid user ID"}), 400

    try:
        conn = psycopg2.connect(DB_PARAMS)
        cur = conn.cursor()

        # Проверяем существование задачи и пользователя
        cur.execute("SELECT id FROM task WHERE id = %s", (task_id,))
        if not cur.fetchone():
            return jsonify({"error": "Task not found"}), 404

        cur.execute("SELECT id FROM \"user\" WHERE id = %s", (user_id,))
        if not cur.fetchone():
            return jsonify({"error": "User not found"}), 404

        # Проверяем, не назначен ли уже пользователь
        cur.execute("SELECT * FROM task_assignees WHERE task_id = %s AND user_id = %s",
                    (task_id, user_id))
        if cur.fetchone():
            return jsonify({"error": "User already assigned to task"}), 400

        cur.execute("INSERT INTO task_assignees (task_id, user_id) VALUES (%s, %s)",
                    (task_id, user_id))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "User assigned to task"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/task/<int:task_id>/unassign', methods=['DELETE'])
def unassign_user_from_task(task_id):
    data = request.json
    user_id = data.get('user_id')

    if not isinstance(user_id, int):
        return jsonify({"error": "Invalid user ID"}), 400

    try:
        conn = psycopg2.connect(DB_PARAMS)
        cur = conn.cursor()

        # Проверяем, существует ли запись в task_assignees
        cur.execute("SELECT * FROM task_assignees WHERE task_id = %s AND user_id = %s",
                    (task_id, user_id))
        if not cur.fetchone():
            return jsonify({"error": "User is not assigned to this task"}), 404

        cur.execute("DELETE FROM task_assignees WHERE task_id = %s AND user_id = %s",
                    (task_id, user_id))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "User unassigned from task"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаем таблицы в базе данных
    app.run(debug=True)
