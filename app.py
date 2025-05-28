from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import csv
from io import StringIO
from flask import Response
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from collections import defaultdict
import os
import plotly.graph_objs as go
import plotly.offline as pyo
from markupsafe import Markup
from flask import session
from flask import jsonify


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SECRET_KEY'] = 'your-secret-key'  # Смените на секретный ключ
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Модель пользователя
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Модель транзакции, связанная с пользователем, добавлено поле currency
class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    category = db.Column(db.String(100))
    amount = db.Column(db.Float)
    currency = db.Column(db.String(10), nullable=False, default='RUB')  # Новое поле
    date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация прошла успешно, теперь войдите в систему')
        return redirect(url_for('login'))
    return render_template('register.html')


# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
    return render_template('login.html')


# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Главная - список транзакций текущего пользователя
@app.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    categories = ['Продукты', 'Транспорт', 'Развлечения', 'Зарплата', 'Другое']
    per_page = 5

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    selected_category = request.args.get('category', '')

    query = Transaction.query.filter_by(user_id=current_user.id)

    if start_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Transaction.date >= start)
    if end_date:
        end = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Transaction.date <= end)
    if selected_category:
        query = query.filter(Transaction.category == selected_category)

    # Пагинация
    pagination = query.order_by(Transaction.date.desc()).paginate(page=page, per_page=per_page)
    transactions = pagination.items



    return render_template('index.html',
                           transactions=transactions,
                           pagination=pagination,
                           start_date=start_date,
                           end_date=end_date,
                           categories=categories,
                           selected_category=selected_category)



# Добавление транзакции с выбором валюты
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    categories = ['Продукты', 'Транспорт', 'Развлечения', 'Зарплата', 'Другое']
    currencies = ['RUB', 'USD', 'EUR', 'UZS']  # Можно расширить список валют
    today = datetime.utcnow().strftime('%Y-%m-%d')
    if request.method == 'POST':
        description = request.form['description']
        category = request.form['category']
        amount = float(request.form['amount'])
        currency = request.form['currency']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')

        new_transaction = Transaction(
            description=description,
            category=category,
            amount=amount,
            currency=currency,
            date=date,
            user_id=current_user.id
        )
        db.session.add(new_transaction)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_transaction.html', today=today, categories=categories, currencies=currencies)


# Редактирование транзакции с выбором валюты
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        flash("Нет доступа к этой транзакции")
        return redirect(url_for('index'))

    categories = ['Продукты', 'Транспорт', 'Развлечения', 'Зарплата', 'Другое']
    currencies = ['RUB', 'USD', 'EUR', 'UZS']

    if request.method == 'POST':
        transaction.description = request.form['description']
        transaction.category = request.form['category']
        transaction.amount = float(request.form['amount'])
        transaction.currency = request.form['currency']
        transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%d')

        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_transaction.html', transaction=transaction, categories=categories, currencies=currencies)


# Удаление транзакции
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        flash("Нет доступа к этой транзакции")
        return redirect(url_for('index'))

    db.session.delete(transaction)
    db.session.commit()
    return redirect(url_for('index'))


# Аналитика за неделю (транзакции текущего пользователя)
@app.route('/weekly-summary')
@login_required
def weekly_summary():
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    summary = {}
    total = 0

    transactions = Transaction.query.filter(Transaction.user_id == current_user.id, Transaction.date >= one_week_ago).all()

    for t in transactions:
        category = t.category or "Не указано"
        summary[category] = summary.get(category, 0) + t.amount
        total += t.amount

    currency = session.get('currency',"Sum")

    return render_template('weekly_summary.html', summary={k: round(v, 2) for k, v in summary.items()}, total=round(total, 2), currency=currency)

@app.route('/export')
@login_required
def export_transactions():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')

    query = Transaction.query.filter_by(user_id=current_user.id)

    if start_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Transaction.date >= start)
    if end_date:
        end = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Transaction.date <= end)
    if category:
        query = query.filter(Transaction.category == category)

    transactions = query.all()

    # Создаем CSV
    si = StringIO()
    cw = csv.writer(si)
    # Заголовки столбцов
    cw.writerow(['Описание', 'Категория', 'Сумма', 'Валюта', 'Дата'])

    for t in transactions:
        cw.writerow([
            t.description,
            t.category,
            f"{t.amount:.2f}",
            t.currency,
            t.date.strftime('%Y-%m-%d')
        ])

    output = si.getvalue()
    si.close()

    # Отправляем CSV как файл
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=transactions.csv"}
    )


@app.route('/export-excel')
@login_required
def export_excel():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')

    query = Transaction.query.filter_by(user_id=current_user.id)

    if start_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Transaction.date >= start)
    if end_date:
        end = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Transaction.date <= end)
    if category:
        query = query.filter(Transaction.category == category)

    transactions = query.all()

    data = [{
        "Описание": t.description,
        "Категория": t.category,
        "Сумма": t.amount,
        "Валюта": t.currency,
        "Дата": t.date.strftime('%Y-%m-%d')
    } for t in transactions]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Транзакции')

    output.seek(0)

    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=transactions.xlsx'}
    )

@app.route("/charts")
@login_required
def charts():
    # Группировка сумм по категориям
    category_totals = defaultdict(float)
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    for t in transactions:
        category_totals[t.category] += t.amount

    # Построение графика
    labels = list(category_totals.keys())
    values = list(category_totals.values())

    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title('Расходы по категориям')

    # Сохраняем график
    chart_path = os.path.join("static", "category_chart.png")
    plt.savefig(chart_path)
    plt.close()

    return render_template("charts.html", chart_url=chart_path)

@app.route("/interactive-charts")
@login_required
def interactive_charts():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    category_totals = {}
    for t in transactions:
        category_totals[t.category] = category_totals.get(t.category, 0) + t.amount

    # Данные для Plotly
    data = [go.Pie(
        labels=list(category_totals.keys()),
        values=list(category_totals.values()),
        hoverinfo='label+percent',
        textinfo='value',
        textfont_size=14
    )]

    layout = go.Layout(title='Интерактивная диаграмма расходов по категориям')
    fig = go.Figure(data=data, layout=layout)
    chart_html = pyo.plot(fig, output_type='div')

    return render_template("interactive_charts.html", chart=Markup(chart_html))

@app.route('/api/weekly_summary')
@login_required
def api_weekly_summary():
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    summary = {}
    total = 0

    transactions = Transaction.query.filter(Transaction.user_id == current_user.id, Transaction.date >= one_week_ago).all()

    for t in transactions:
        category = t.category or "Не указано"
        if category not in summary:
            summary[category] = {"amount": 0, "currency": t.currency}
        summary[category]["amount"] += t.amount
        total += t.amount

    # округляем суммы
    for cat in summary:
        summary[cat]["amount"] = round(summary[cat]["amount"], 2)
    total = round(total, 2)

    return jsonify(summary=summary, total=total)
@app.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    user_budget = current_user.budget
    if request.method == 'POST':
        amount = float(request.form['amount'])
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

        if user_budget:
            user_budget.amount = amount
            user_budget.start_date = start_date
            user_budget.end_date = end_date
        else:
            user_budget = Budget(amount=amount, start_date=start_date, end_date=end_date, user_id=current_user.id)
            db.session.add(user_budget)

        db.session.commit()
        flash('Бюджет обновлен')
        return redirect(url_for('index'))

    return render_template('budget.html', budget=user_budget)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
