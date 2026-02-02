# game_subs_app.py
# Game Subscription Service с PostgreSQL

import sys
import os
import hashlib
from datetime import datetime, timedelta, date
from pathlib import Path
from decimal import Decimal

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QListWidget, QListWidgetItem,
    QTextEdit, QFormLayout, QComboBox, QSpinBox, QFileDialog, QDateEdit, QTableWidget,
    QTableWidgetItem, QGroupBox, QGridLayout, QSizePolicy, QSpacerItem, QDialog,
    QDialogButtonBox, QHeaderView, QTabWidget, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QIcon

# Импортируем модуль базы данных
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import db

# Планы подписок
PLANS = {
    "Basic": {"days": 30, "price": 299},
    "Premium": {"days": 90, "price": 699}
}


# -----------------------------
# Helper функции для работы с БД PostgreSQL
# -----------------------------
def hash_password(pw: str):
    """Хеширование пароля"""
    return hashlib.sha256(pw.encode()).hexdigest()


def find_user_by_username(username):
    """Найти пользователя по имени"""
    return db.get_user_by_username(username)


def find_user_by_id(uid):
    """Найти пользователя по ID"""
    return db.get_user_by_id(uid)


def find_game_by_id(gid):
    """Найти игру по ID"""
    return db.get_game_by_id(gid)


def get_subscription_status(user):
    """Получить статус подписки пользователя"""
    if not user:
        return None
    subscription = db.get_user_subscription(user["id"])
    if not subscription:
        return None
    return {"plan": subscription["plan"], "end_date": subscription["end_date"]}


def get_user_library(user):
    """Возвращает все игры в библиотеке пользователя (объединение купленных и полученных по подписке)"""
    if not user:
        return []

    purchased = db.get_user_purchased_games(user["id"])
    subscribed = db.get_user_subscribed_games(user["id"])

    library = set(purchased)
    library.update(subscribed)
    return list(library)


# -----------------------------
# Диалог для просмотра описания игры
# -----------------------------
class GameDescriptionDialog(QDialog):
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.setWindowTitle(f"Описание игры: {game['title']}")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(f"<h2>{self.game['title']}</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        info_label = QLabel(f"""
        <b>Жанр:</b> {self.game.get('genre', 'Не указан')}<br>
        <b>Разработчик:</b> {self.game.get('developer', 'Не указан')}<br>
        <b>Дата выхода:</b> {self.game.get('release_date', 'Не указана')}<br>
        <b>Цена:</b> {self.game.get('price', 0)} руб.<br>
        <b>Тип подписки:</b> {self.get_subscription_type_text(self.game.get('subscription_type', 'none'))}
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        description_label = QLabel("<b>Описание:</b>")
        layout.addWidget(description_label)

        description_text = QTextEdit()
        description_text.setPlainText(self.game.get('description', 'Нет описания'))
        description_text.setReadOnly(True)
        layout.addWidget(description_text)

        btn_close = QPushButton("Закрыть")
        btn_close.setMinimumHeight(40)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.setLayout(layout)

    def get_subscription_type_text(self, sub_type):
        if sub_type == "premium":
            return "Premium подписка"
        elif sub_type == "basic":
            return "Basic подписка"
        else:
            return "Не доступна по подписке"


# -----------------------------
# UI Components - Адаптированные для работы с PostgreSQL
# -----------------------------
class LoginWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        lbl = QLabel("🎮 Game Subscription Service с PostgreSQL")
        lbl.setAlignment(Qt.AlignCenter)
        lbl_font = QFont()
        lbl_font.setPointSize(24)
        lbl_font.setBold(True)
        lbl.setFont(lbl_font)
        lbl.setStyleSheet("color: #2c3e50; margin-bottom: 30px;")
        layout.addWidget(lbl)

        form_group = QGroupBox("Вход в систему")
        form_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Введите имя пользователя")
        self.username_edit.setMinimumHeight(35)
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Введите пароль")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(35)

        form_layout.addRow("Имя пользователя:", self.username_edit)
        form_layout.addRow("Пароль:", self.password_edit)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        btn_login = QPushButton("Войти")
        btn_login.setMinimumHeight(45)
        btn_login.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        btn_register = QPushButton("Зарегистрироваться")
        btn_register.setMinimumHeight(40)
        btn_register.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)

        layout.addWidget(btn_login)
        layout.addWidget(btn_register)

        # Кнопка выхода из приложения
        btn_exit = QPushButton("🚪 Выйти из приложения")
        btn_exit.setMinimumHeight(40)
        btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        btn_exit.clicked.connect(self.exit_app)
        layout.addWidget(btn_exit)

        test_label = QLabel("Тестовые данные:\nadmin / admin123\nили\ngamer01 / password")
        test_label.setAlignment(Qt.AlignCenter)
        test_label.setStyleSheet("color: #333333; font-style: italic; margin-top: 20px; font-size: 13px;")
        layout.addWidget(test_label)

        btn_login.clicked.connect(self.try_login)
        btn_register.clicked.connect(lambda: self.app_ref.show_register())

        self.setLayout(layout)

    def try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите имя пользователя и пароль.")
            return

        user = find_user_by_username(username)
        if not user:
            QMessageBox.warning(self, "Ошибка", "Пользователь не найден.")
            return

        if user["password_hash"] != hash_password(password):
            QMessageBox.warning(self, "Ошибка", "Неверный пароль.")
            return

        self.app_ref.current_user = user

        subs = get_subscription_status(user)
        if subs:
            days_left = (subs["end_date"] - date.today()).days
            if days_left < 0:
                QMessageBox.information(self, "Подписка",
                                        f"Ваша подписка {subs['plan']} истекла {subs['end_date'].isoformat()}.")
            elif days_left <= 3:
                QMessageBox.information(self, "Подписка",
                                        f"Ваша подписка {subs['plan']} истекает через {days_left} дней ({subs['end_date'].isoformat()}).")

        # Обновляем данные в главном окне
        self.app_ref.refresh_data()
        self.app_ref.show_main_menu()

    def exit_app(self):
        """Выход из приложения"""
        reply = QMessageBox.question(self, 'Выход из приложения',
                                     'Вы уверены, что хотите выйти из приложения?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()


class RegisterWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Регистрация нового аккаунта")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)

        form_group = QGroupBox("Заполните данные")
        form_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Придумайте имя пользователя")
        self.username.setMinimumHeight(35)
        self.email = QLineEdit()
        self.email.setPlaceholderText("example@mail.com")
        self.email.setMinimumHeight(35)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Минимум 6 символов")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(35)
        self.confirm = QLineEdit()
        self.confirm.setPlaceholderText("Повторите пароль")
        self.confirm.setEchoMode(QLineEdit.Password)
        self.confirm.setMinimumHeight(35)

        form_layout.addRow("Имя пользователя:", self.username)
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Пароль:", self.password)
        form_layout.addRow("Подтверждение:", self.confirm)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        btn_layout = QHBoxLayout()
        btn_create = QPushButton("Создать аккаунт")
        btn_create.setMinimumHeight(45)
        btn_create.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)

        btn_back = QPushButton("Назад")
        btn_back.setMinimumHeight(40)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)

        btn_layout.addWidget(btn_create)
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        # Кнопка выхода из приложения
        btn_exit = QPushButton("🚪 Выйти из приложения")
        btn_exit.setMinimumHeight(40)
        btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        btn_exit.clicked.connect(self.exit_app)
        layout.addWidget(btn_exit)

        btn_create.clicked.connect(self.create_account)
        btn_back.clicked.connect(lambda: self.app_ref.show_login())

        self.setLayout(layout)

    def create_account(self):
        u = self.username.text().strip()
        e = self.email.text().strip()
        p = self.password.text()
        c = self.confirm.text()

        if not u or not e or not p:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля.")
            return
        if len(p) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать минимум 6 символов.")
            return
        if p != c:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return

        if find_user_by_username(u):
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким именем уже существует.")
            return

        user = db.create_user(u, e, p, "user")
        if not user:
            QMessageBox.warning(self, "Ошибка", "Ошибка при создании пользователя.")
            return

        QMessageBox.information(self, "Успех", "Аккаунт создан. Войдите в систему.")
        self.app_ref.refresh_data()
        self.app_ref.show_login()

    def exit_app(self):
        """Выход из приложения"""
        reply = QMessageBox.question(self, 'Выход из приложения',
                                     'Вы уверены, что хотите выйти из приложения?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()


class MainMenuWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("🎮 Game Subscription Service")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title)

        self.greeting = QLabel("")
        self.greeting.setAlignment(Qt.AlignCenter)
        self.greeting.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 8px;
                font-size: 14px;
                color: #333333;
            }
        """)
        main_layout.addWidget(self.greeting)

        self.stat_label = QLabel("")
        self.stat_label.setAlignment(Qt.AlignCenter)
        self.stat_label.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-size: 13px;
            }
        """)
        main_layout.addWidget(self.stat_label)

        grid = QGridLayout()
        grid.setSpacing(15)

        btn_catalog = self.create_menu_button("📁 Каталог игр", "#3498db")
        btn_lib = self.create_menu_button("🎮 Моя библиотека", "#9b59b6")
        btn_sub = self.create_menu_button("💰 Подписка", "#2ecc71")
        btn_profile = self.create_menu_button("👤 Личный кабинет", "#e74c3c")

        grid.addWidget(btn_catalog, 0, 0)
        grid.addWidget(btn_lib, 0, 1)
        grid.addWidget(btn_sub, 1, 0)
        grid.addWidget(btn_profile, 1, 1)

        main_layout.addLayout(grid)

        self.btn_admin = QPushButton("⚙️ Панель разработчика (Admin)")
        self.btn_admin.setMinimumHeight(50)
        self.btn_admin.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)
        self.btn_admin.clicked.connect(lambda: self.app_ref.show_admin_panel())
        main_layout.addWidget(self.btn_admin)

        # Кнопка выхода из приложения
        btn_exit = QPushButton("🚪 Выйти из приложения")
        btn_exit.setMinimumHeight(50)
        btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        btn_exit.clicked.connect(self.exit_app)
        main_layout.addWidget(btn_exit)

        btn_catalog.clicked.connect(lambda: self.app_ref.show_catalog())
        btn_lib.clicked.connect(lambda: self.app_ref.show_library())
        btn_sub.clicked.connect(lambda: self.app_ref.show_subscription())
        btn_profile.clicked.connect(lambda: self.app_ref.show_profile())

        self.setLayout(main_layout)

    def create_menu_button(self, text, color):
        btn = QPushButton(text)
        btn.setMinimumHeight(80)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        return btn

    def refresh(self):
        user = self.app_ref.current_user
        if not user:
            return

        subs = get_subscription_status(user)
        plan_text = "Нет активной подписки"
        if subs:
            days_left = (subs["end_date"] - date.today()).days
            if days_left > 0:
                plan_text = f"{subs['plan']} (до {subs['end_date'].isoformat()}, осталось {days_left} дней)"
            else:
                plan_text = f"{subs['plan']} (истекла {subs['end_date'].isoformat()})"
        self.greeting.setText(f"👋 Добро пожаловать, {user['username']}!\n📊 Ваша подписка: {plan_text}")

        stats = db.get_statistics()
        self.stat_label.setText(
            f"📈 Статистика системы: Активных подписок: {stats['active_subscriptions']} • Пользователей: {stats['total_users']} • Игр в каталоге: {stats['total_games']}")

        self.btn_admin.setVisible(user.get("role") == "admin")

    def exit_app(self):
        """Выход из приложения"""
        reply = QMessageBox.question(self, 'Выход из приложения',
                                     'Вы уверены, что хотите выйти из приложения?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()


class CatalogWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        lbl = QLabel("📁 Каталог игр")
        lbl.setStyleSheet("font-weight: bold; font-size: 20px; color: #2c3e50;")
        header_layout.addWidget(lbl)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Поиск по названию, жанру...")
        self.search_edit.setMinimumHeight(35)
        btn_search = QPushButton("Найти")
        btn_search.setMinimumHeight(35)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        header_layout.addWidget(self.search_edit)
        header_layout.addWidget(btn_search)
        main_layout.addLayout(header_layout)

        content = QHBoxLayout()
        content.setSpacing(15)

        games_group = QGroupBox("Список игр")
        games_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        games_layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(350)
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 14px;
                padding: 5px;
                background-color: #2c3e50;
                color: white;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #4a5a6a;
                color: white;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        games_layout.addWidget(self.list_widget)
        games_group.setLayout(games_layout)
        content.addWidget(games_group)

        details_group = QGroupBox("Детали игры")
        details_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        details_layout = QVBoxLayout()

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(200)
        self.detail.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333333;
                background-color: white;
            }
        """)
        details_layout.addWidget(self.detail)

        btn_add_lib = QPushButton("➕ Добавить в библиотеку")
        btn_add_lib.setMinimumHeight(40)
        btn_add_lib.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)

        btn_buy = QPushButton("💰 Купить отдельно")
        btn_buy.setMinimumHeight(40)
        btn_buy.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)

        btn_refresh = QPushButton("🔄 Обновить список")
        btn_refresh.setMinimumHeight(35)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)

        details_layout.addWidget(btn_add_lib)
        details_layout.addWidget(btn_buy)
        details_layout.addWidget(btn_refresh)
        details_group.setLayout(details_layout)
        content.addWidget(details_group)

        main_layout.addLayout(content)

        btn_back = QPushButton("⬅ Назад в меню")
        btn_back.setMinimumHeight(40)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        main_layout.addWidget(btn_back)

        btn_back.clicked.connect(lambda: self.app_ref.show_main_menu())
        btn_search.clicked.connect(self.search)
        self.list_widget.itemClicked.connect(self.show_detail)
        btn_add_lib.clicked.connect(self.add_to_library)
        btn_buy.clicked.connect(self.buy_game)
        btn_refresh.clicked.connect(self.populate)

        self.setLayout(main_layout)
        self.populate()

    def populate(self):
        self.list_widget.clear()
        self.detail.clear()
        games = db.get_all_games()
        for g in sorted(games, key=lambda x: x["title"].lower()):
            sub_type = g.get("subscription_type", "none")
            if sub_type == "premium":
                subtext = "✅ Premium подписка"
            elif sub_type == "basic":
                subtext = "✅ Basic подписка"
            else:
                subtext = "❌ Только покупка"
            price_text = f"💰 {g.get('price', 0)} руб."
            item = QListWidgetItem(f"{g['title']} | {g['genre']} | {subtext} | {price_text}")
            item.setData(Qt.UserRole, g["id"])
            self.list_widget.addItem(item)

    def search(self):
        q = self.search_edit.text().strip().lower()
        if not q:
            self.populate()
            return

        self.list_widget.clear()
        self.detail.clear()
        games = db.search_games(q)
        for g in games:
            sub_type = g.get("subscription_type", "none")
            if sub_type == "premium":
                subtext = "✅ Premium подписка"
            elif sub_type == "basic":
                subtext = "✅ Basic подписка"
            else:
                subtext = "❌ Только покупка"
            price_text = f"💰 {g.get('price', 0)} руб."
            item = QListWidgetItem(f"{g['title']} | {g['genre']} | {subtext} | {price_text}")
            item.setData(Qt.UserRole, g["id"])
            self.list_widget.addItem(item)

    def show_detail(self, item):
        gid = item.data(Qt.UserRole)
        g = find_game_by_id(gid)
        if g:
            sub_type = g.get("subscription_type", "none")
            if sub_type == "premium":
                subscription_status = "✅ Доступна по Premium подписке"
            elif sub_type == "basic":
                subscription_status = "✅ Доступна по Basic и Premium подписке"
            else:
                subscription_status = "❌ Только отдельная покупка"
            text = f"""
🎮 <b>{g['title']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Жанр:</b> {g['genre']}
<b>Разработчик:</b> {g.get('developer', 'Не указан')}
<b>Дата выхода:</b> {g.get('release_date', 'Не указана')}
<b>Цена:</b> {g.get('price', 0)} руб.
<b>Статус:</b> {subscription_status}

<b>Описание:</b>
{g.get('description', 'Нет описания')}
            """
            self.detail.setHtml(text)

    def add_to_library(self):
        selected = self.list_widget.currentItem()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите игру из списка.")
            return
        gid = selected.data(Qt.UserRole)
        user = self.app_ref.current_user
        g = find_game_by_id(gid)

        library = get_user_library(user)
        if gid in library:
            QMessageBox.information(self, "Информация", f"Игра '{g['title']}' уже находится в вашей библиотеке.")
            return

        subs = get_subscription_status(user)
        game_sub_type = g.get("subscription_type", "none")

        if game_sub_type != "none" and subs:
            if subs["plan"] == "Premium" or (subs["plan"] == "Basic" and game_sub_type == "basic"):
                if db.add_subscribed_game(user["id"], gid):
                    QMessageBox.information(self, "Успех",
                                            f"Игра '{g['title']}' добавлена в вашу библиотеку по подписке.")
                    self.app_ref.refresh_data()
                return

        QMessageBox.information(self, "Информация",
                                f"Игра '{g['title']}' не входит в вашу подписку.\nИспользуйте кнопку 'Купить отдельно' для приобретения.")

    def buy_game(self):
        selected = self.list_widget.currentItem()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для покупки.")
            return
        gid = selected.data(Qt.UserRole)
        g = find_game_by_id(gid)
        user = self.app_ref.current_user

        library = get_user_library(user)
        if gid in library:
            QMessageBox.information(self, "Информация", f"Игра '{g['title']}' уже есть в вашей библиотеке.")
            return

        confirm = QMessageBox.question(self, "Подтверждение покупки",
                                       f"Вы уверены, что хотите купить игру:\n\n<b>{g['title']}</b>\nза <b>{g['price']} руб.</b>?",
                                       QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            if db.add_purchased_game(user["id"], gid):
                QMessageBox.information(self, "Успех",
                                        f"Покупка выполнена успешно!\nИгра '{g['title']}' добавлена в вашу библиотеку.")
                self.app_ref.refresh_data()


class LibraryWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("🎮 Моя библиотека")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 20px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(lbl)

        self.counter_label = QLabel("Игр в библиотеке: 0")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet("color: #333333; font-size: 14px;")
        layout.addWidget(self.counter_label)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(300)
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 14px;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 5px;
                color: #333333;
                background-color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
                color: #333333;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_desc = QPushButton("📖 Описание")
        btn_desc.setMinimumHeight(45)
        btn_desc.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        btn_remove = QPushButton("🗑️ Удалить из библиотеки")
        btn_remove.setMinimumHeight(45)
        btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        btn_launch = QPushButton("▶️ Запустить игру")
        btn_launch.setMinimumHeight(45)
        btn_launch.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)

        btn_back = QPushButton("⬅ Назад в меню")
        btn_back.setMinimumHeight(45)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)

        btn_layout.addWidget(btn_desc)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_launch)
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        btn_desc.clicked.connect(self.show_description)
        btn_remove.clicked.connect(self.remove_game)
        btn_launch.clicked.connect(self.launch_game)
        btn_back.clicked.connect(lambda: self.app_ref.show_main_menu())
        self.setLayout(layout)

    def refresh(self):
        self.list_widget.clear()
        user = self.app_ref.current_user
        if not user:
            return

        library = get_user_library(user)
        library_count = len(library)
        self.counter_label.setText(f"Игр в библиотеке: {library_count}")

        subs = get_subscription_status(user)
        sub_active = False
        if subs:
            days_left = (subs["end_date"] - date.today()).days
            sub_active = days_left > 0

        for gid in library:
            g = find_game_by_id(gid)
            if g:
                purchased_games = db.get_user_purchased_games(user["id"])
                subscribed_games = db.get_user_subscribed_games(user["id"])

                if gid in purchased_games:
                    game_type = "💰 Куплена"
                elif gid in subscribed_games:
                    if sub_active:
                        game_type = "✅ По подписке (активно)"
                    else:
                        game_type = "⚠️ По подписке (НЕАКТИВНО)"
                else:
                    game_type = "📁 В библиотеке"

                item = QListWidgetItem(f"{g['title']} | {g['genre']} | {game_type}")
                item.setData(Qt.UserRole, g["id"])

                # Подсветка игр по подписке, если подписка неактивна
                if gid in subscribed_games and not sub_active:
                    item.setForeground(Qt.red)

                self.list_widget.addItem(item)

    def show_description(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для просмотра описания.")
            return
        gid = item.data(Qt.UserRole)
        g = find_game_by_id(gid)
        if g:
            dlg = GameDescriptionDialog(g, self)
            dlg.exec()

    def remove_game(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для удаления.")
            return

        gid = item.data(Qt.UserRole)
        g = find_game_by_id(gid)
        user = self.app_ref.current_user

        purchased_games = db.get_user_purchased_games(user["id"])
        subscribed_games = db.get_user_subscribed_games(user["id"])

        if gid in purchased_games:
            confirm = QMessageBox.question(self, "Подтверждение",
                                           f"Вы уверены, что хотите удалить купленную игру '{g['title']}' из библиотеки?\nВы больше не сможете получить её обратно без повторной покупки.",
                                           QMessageBox.Yes | QMessageBox.No)

            if confirm == QMessageBox.Yes:
                if db.remove_purchased_game(user["id"], gid):
                    QMessageBox.information(self, "Успех", "Игра удалена из библиотеки.")
                    self.app_ref.refresh_data()
                    self.refresh()
        elif gid in subscribed_games:
            QMessageBox.warning(self, "Ошибка",
                                "Игры, полученные по подписке, нельзя удалить. Отмените подписку, чтобы удалить эти игры.")
        else:
            QMessageBox.warning(self, "Ошибка", "Игра не найдена в вашей библиотеке.")

    def launch_game(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для запуска.")
            return
        gid = item.data(Qt.UserRole)
        g = find_game_by_id(gid)
        user = self.app_ref.current_user

        purchased_games = db.get_user_purchased_games(user["id"])
        subscribed_games = db.get_user_subscribed_games(user["id"])

        if gid in purchased_games:
            QMessageBox.information(self, "Запуск игры",
                                    f"Запуск игры '{g['title']}'...\n\n(В демо-версии это симуляция запуска)")
            return

        if gid in subscribed_games:
            sub = get_subscription_status(user)
            if sub and sub["end_date"] >= date.today():
                QMessageBox.information(self, "Запуск игры",
                                        f"Запуск игры '{g['title']}'...\n\n(В демо-версии это симуляция запуска)")
            else:
                QMessageBox.warning(self, "Ошибка",
                                    f"Игра '{g['title']}' доступна по подписке, но ваша подписка неактивна или истекла.\nПродлите подписку для доступа к игре.")
            return

        QMessageBox.warning(self, "Ошибка", "Игра не найдена в вашей библиотеке.")


class SubscriptionWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        lbl = QLabel("💰 Мои подписки")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 24px; color: #2c3e50;")
        layout.addWidget(lbl)

        current_box = QGroupBox("📊 Текущая подписка")
        current_box.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        current_layout = QVBoxLayout()
        self.current_label = QLabel("Загрузка информации...")
        self.current_label.setWordWrap(True)
        self.current_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 8px;
                color: #333333;
            }
        """)
        current_layout.addWidget(self.current_label)
        current_box.setLayout(current_layout)
        layout.addWidget(current_box)

        plans_box = QGroupBox("🎯 Доступные планы подписки")
        plans_box.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        p_layout = QVBoxLayout()

        for plan_name, p in PLANS.items():
            plan_widget = QWidget()
            plan_layout = QHBoxLayout()

            info_label = QLabel(f"<b>{plan_name}</b><br>{p['days']} дней<br>{p['price']} руб.")
            info_label.setStyleSheet("font-size: 14px; padding: 10px; color: #333333;")

            btn = QPushButton("Оформить")
            btn.setMinimumHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                    font-weight: bold;
                    border-radius: 5px;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
                QPushButton:disabled {
                    background-color: #95a5a6;
                }
            """)
            btn.clicked.connect(lambda _, pn=plan_name: self.buy_plan(pn))

            plan_layout.addWidget(info_label)
            plan_layout.addStretch()
            plan_layout.addWidget(btn)
            plan_widget.setLayout(plan_layout)
            p_layout.addWidget(plan_widget)

            if plan_name != list(PLANS.keys())[-1]:
                line = QLabel()
                line.setFrameShape(QLabel.HLine)
                line.setStyleSheet("background-color: #ddd;")
                p_layout.addWidget(line)

        plans_box.setLayout(p_layout)
        layout.addWidget(plans_box)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_extend = QPushButton("⏳ Продлить подписку")
        btn_extend.setMinimumHeight(45)
        btn_extend.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        btn_cancel = QPushButton("❌ Отменить подписку")
        btn_cancel.setMinimumHeight(45)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        btn_back = QPushButton("⬅ Назад в меню")
        btn_back.setMinimumHeight(45)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)

        btn_layout.addWidget(btn_extend)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        btn_extend.clicked.connect(self.extend_subscription)
        btn_cancel.clicked.connect(self.cancel_subscription)
        btn_back.clicked.connect(lambda: self.app_ref.show_main_menu())

        self.setLayout(layout)

    def refresh(self):
        u = self.app_ref.current_user
        if not u:
            self.current_label.setText("Нет активного пользователя.")
            return

        sub = get_subscription_status(u)
        if sub:
            days_left = (sub["end_date"] - date.today()).days
            status_color = "#2ecc71" if days_left > 7 else ("#f39c12" if days_left > 0 else "#e74c3c")
            status_text = "Активна" if days_left > 0 else "Истекла"

            # Сбрасываем состояние кнопок
            for i in range(self.layout().itemAt(1).widget().layout().count()):
                widget = self.layout().itemAt(1).widget().layout().itemAt(i).widget()
                if widget and isinstance(widget, QWidget):
                    for child in widget.children():
                        if isinstance(child, QPushButton):
                            if sub["plan"] == "Premium":
                                if child.text() == "Оформить" and widget.layout().itemAt(0).widget().text().find(
                                        "Premium") != -1:
                                    child.setEnabled(False)
                                    child.setText("Уже активна")
                            elif sub["plan"] == "Basic":
                                if child.text() == "Оформить" and widget.layout().itemAt(0).widget().text().find(
                                        "Basic") != -1:
                                    child.setEnabled(False)
                                    child.setText("Уже активна")

            self.current_label.setText(f"""
                <div style='color: {status_color}; font-weight: bold;'>📋 {sub['plan']} — {status_text}</div>
                <div style='margin-top: 10px; color: #333333;'>
                <b>Срок действия:</b> {sub['end_date'].isoformat()}<br>
                <b>Осталось дней:</b> {days_left if days_left > 0 else 0}<br>
                <b>Доступно игр по подписке:</b> {sum(1 for g in db.get_all_games() if g.get('subscription_type') != 'none')}<br>
                <b>Игр по подписке в вашей библиотеке:</b> {len(db.get_user_subscribed_games(u['id']))}
                </div>
            """)
        else:
            self.current_label.setText("""
                <div style='color: #e74c3c; font-weight: bold;'>❌ Нет активной подписки</div>
                <div style='margin-top: 10px; color: #333333;'>
                У вас нет активной подписки.<br>
                Оформите подписку, чтобы получить доступ к играм из каталога.
                </div>
            """)

    def buy_plan(self, plan_name):
        u = self.app_ref.current_user
        if not u:
            QMessageBox.warning(self, "Ошибка", "Сначала войдите в систему.")
            return

        sub = get_subscription_status(u)

        if sub:
            if sub["plan"] == plan_name:
                QMessageBox.information(self, "Информация",
                                        f"У вас уже активна подписка {plan_name}. Используйте кнопку 'Продлить подписку'.")
                return
            elif sub["plan"] == "Premium":
                QMessageBox.warning(self, "Ошибка",
                                    "У вас уже активна подписка Premium. Вы не можете оформить другую подписку.")
                return
            elif sub["plan"] == "Basic" and plan_name == "Premium":
                confirm = QMessageBox.question(self, "Улучшение подписки",
                                               f"Вы хотите улучшить вашу подписку с Basic до Premium?\n\n"
                                               f"Разница в цене: {PLANS['Premium']['price'] - PLANS['Basic']['price']} руб.\n"
                                               f"Дополнительные дни: {PLANS['Premium']['days'] - PLANS['Basic']['days']} дней\n\n"
                                               f"Подтвердить улучшение?",
                                               QMessageBox.Yes | QMessageBox.No)

                if confirm != QMessageBox.Yes:
                    return

                current_end = sub["end_date"]
                days_to_add = PLANS["Premium"]["days"] - PLANS["Basic"]["days"]
                new_end = current_end + timedelta(days=days_to_add)

                subscription = db.create_or_update_subscription(u["id"], "Premium", new_end)
                if subscription:
                    self.add_subscription_games(u, "Premium")
                    QMessageBox.information(self, "Успех",
                                            f"Подписка успешно улучшена до Premium!\nСрок действия: до {new_end.isoformat()}")
                    self.app_ref.refresh_data()
                    self.refresh()
                return

        plan = PLANS[plan_name]
        confirm = QMessageBox.question(self, "Оформление подписки",
                                       f"Оформить подписку <b>{plan_name}</b> на {plan['days']} дней за {plan['price']} руб.?",
                                       QMessageBox.Yes | QMessageBox.No)

        if confirm != QMessageBox.Yes:
            return

        end_date = date.today() + timedelta(days=plan["days"])
        subscription = db.create_or_update_subscription(u["id"], plan_name, end_date)

        if subscription:
            self.add_subscription_games(u, plan_name)
            QMessageBox.information(self, "Успех",
                                    f"Подписка <b>{plan_name}</b> успешно активирована!\nСрок действия: до {end_date.isoformat()}")
            self.app_ref.refresh_data()
            self.refresh()

    def add_subscription_games(self, user, plan):
        """Добавляет игры по подписке в библиотеку пользователя"""
        games = db.get_all_games()
        for game in games:
            game_sub_type = game.get("subscription_type", "none")
            if game_sub_type == "none":
                continue
            if plan == "Premium" or (plan == "Basic" and game_sub_type == "basic"):
                db.add_subscribed_game(user["id"], game["id"])

    def extend_subscription(self):
        u = self.app_ref.current_user
        if not u:
            QMessageBox.warning(self, "Ошибка", "Сначала войдите в систему.")
            return

        sub = get_subscription_status(u)
        if not sub:
            QMessageBox.information(self, "Информация", "У вас нет активной подписки. Выберите план ниже.")
            return

        current_end = sub["end_date"]
        if current_end < date.today():
            current_end = date.today()

        new_end = current_end + timedelta(days=30)

        confirm = QMessageBox.question(self, "Продление подписки",
                                       f"Продлить вашу подписку {sub['plan']} на 30 дней?\n"
                                       f"Новая дата окончания: {new_end.isoformat()}",
                                       QMessageBox.Yes | QMessageBox.No)

        if confirm != QMessageBox.Yes:
            return

        subscription = db.extend_subscription(u["id"], 30)
        if subscription:
            QMessageBox.information(self, "Успех", f"Подписка продлена до {new_end.isoformat()}.")
            self.app_ref.refresh_data()
            self.refresh()

    def cancel_subscription(self):
        u = self.app_ref.current_user
        if not u:
            QMessageBox.warning(self, "Ошибка", "Сначала войдите в систему.")
            return

        sub = get_subscription_status(u)
        if not sub:
            QMessageBox.information(self, "Информация", "У вас нет активной подписки.")
            return

        confirm = QMessageBox.question(self, "Отмена подписки",
                                       "Вы уверены, что хотите отменить подписку?\n"
                                       "Доступ к играм по подписке будет прекращен, и эти игры удалятся из вашей библиотеки.",
                                       QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            if db.cancel_subscription(u["id"]):
                QMessageBox.information(self, "Подписка отменена", "Ваша подписка была успешно отменена.")
                self.app_ref.refresh_data()
                self.refresh()


class ProfileWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        lbl = QLabel("👤 Личный кабинет")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 24px; color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(lbl)

        info_box = QGroupBox("📋 Информация о пользователе")
        info_box.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        info_layout = QVBoxLayout()
        self.info_label = QLabel("Загрузка информации...")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 20px;
                background-color: #ecf0f1;
                border-radius: 8px;
                line-height: 1.5;
                color: #333333;
            }
        """)
        info_layout.addWidget(self.info_label)
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)

        btn_layout = QGridLayout()
        btn_layout.setSpacing(10)

        btn_change_pw = QPushButton("🔐 Изменить пароль")
        btn_change_pw.setMinimumHeight(45)
        btn_change_pw.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        btn_delete = QPushButton("🗑️ Удалить аккаунт")
        btn_delete.setMinimumHeight(45)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        btn_logout = QPushButton("🚪 Выйти из системы")
        btn_logout.setMinimumHeight(45)
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)

        btn_back = QPushButton("⬅ Назад в меню")
        btn_back.setMinimumHeight(45)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)

        btn_layout.addWidget(btn_change_pw, 0, 0)
        btn_layout.addWidget(btn_delete, 0, 1)
        btn_layout.addWidget(btn_logout, 1, 0)
        btn_layout.addWidget(btn_back, 1, 1)

        layout.addLayout(btn_layout)

        btn_change_pw.clicked.connect(self.change_password)
        btn_delete.clicked.connect(self.delete_account)
        btn_logout.clicked.connect(self.logout)
        btn_back.clicked.connect(lambda: self.app_ref.show_main_menu())

        self.setLayout(layout)

    def refresh(self):
        u = self.app_ref.current_user
        if not u:
            self.info_label.setText("Нет активного пользователя.")
            return

        sub = get_subscription_status(u)
        sub_text = "Нет активной подписки"
        if sub:
            days_left = (sub["end_date"] - date.today()).days
            sub_text = f"{sub['plan']} (до {sub['end_date'].isoformat()}, осталось {days_left} дней)"

        library = get_user_library(u)
        purchased_count = len(db.get_user_purchased_games(u["id"]))
        subscribed_count = len(db.get_user_subscribed_games(u["id"]))

        text = f"""
        <b style="color: #333333;">👤 Имя пользователя:</b> {u['username']}<br>
        <b style="color: #333333;">📧 Email:</b> {u['email']}<br>
        <b style="color: #333333;">🎭 Роль:</b> {u['role']}<br>
        <b style="color: #333333;">📅 Дата регистрации:</b> {u['reg_date']}<br>
        <b style="color: #333333;">💰 Подписка:</b> {sub_text}<br>
        <b style="color: #333333;">🎮 Игр в библиотеке:</b> {len(library)}<br>
        <b style="color: #333333;">🛒 Купленных игр:</b> {purchased_count}<br>
        <b style="color: #333333;">📋 Игр по подписке:</b> {subscribed_count}<br>
        <b style="color: #333333;">🆔 ID пользователя:</b> {u['id']}
        """
        self.info_label.setText(text)

    def change_password(self):
        u = self.app_ref.current_user
        if not u:
            QMessageBox.warning(self, "Ошибка", "Сначала войдите в систему.")
            return
        dlg = PasswordChangeDialog(self.app_ref)
        dlg.exec()

    def delete_account(self):
        u = self.app_ref.current_user
        if not u:
            QMessageBox.warning(self, "Ошибка", "Сначала войдите в систему.")
            return

        confirm = QMessageBox.warning(self, "Удаление аккаунта",
                                      "⚠️ <b>ВНИМАНИЕ!</b><br><br>"
                                      "Вы уверены, что хотите удалить свой аккаунт?<br>"
                                      "Это действие <b>необратимо</b> и удалит все ваши данные.",
                                      QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            if db.delete_user(u["id"]):
                QMessageBox.information(self, "Аккаунт удалён", "Ваш аккаунт был успешно удалён.")
                self.app_ref.current_user = None
                self.app_ref.show_login()

    def logout(self):
        self.app_ref.current_user = None
        self.app_ref.show_login()


class PasswordChangeDialog(QDialog):
    def __init__(self, app_ref):
        super().__init__(app_ref)
        self.app_ref = app_ref
        self.setWindowTitle("Изменение пароля")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("🔐 Изменение пароля")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 18px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(lbl)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.old = QLineEdit()
        self.old.setPlaceholderText("Введите текущий пароль")
        self.old.setEchoMode(QLineEdit.Password)
        self.old.setMinimumHeight(35)

        self.new = QLineEdit()
        self.new.setPlaceholderText("Введите новый пароль (мин. 6 символов)")
        self.new.setEchoMode(QLineEdit.Password)
        self.new.setMinimumHeight(35)

        self.confirm = QLineEdit()
        self.confirm.setPlaceholderText("Подтвердите новый пароль")
        self.confirm.setEchoMode(QLineEdit.Password)
        self.confirm.setMinimumHeight(35)

        form_layout.addRow("Текущий пароль:", self.old)
        form_layout.addRow("Новый пароль:", self.new)
        form_layout.addRow("Подтверждение:", self.confirm)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Сменить пароль")
        button_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
            }
        """)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
            }
        """)
        button_box.accepted.connect(self.change_password)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333333;
            }
            QLabel {
                color: #333333;
            }
        """)

        self.setLayout(layout)

    def change_password(self):
        old = self.old.text()
        new = self.new.text()
        conf = self.confirm.text()

        u = self.app_ref.current_user
        if not u:
            QMessageBox.warning(self, "Ошибка", "Нет активного пользователя.")
            return

        if hash_password(old) != u["password_hash"]:
            QMessageBox.warning(self, "Ошибка", "Текущий пароль неверен.")
            return

        if len(new) < 6:
            QMessageBox.warning(self, "Ошибка", "Новый пароль должен содержать минимум 6 символов.")
            return

        if new != conf or not new:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return

        if db.update_user_password(u["id"], new):
            QMessageBox.information(self, "Успех", "Пароль успешно изменён.")
            self.app_ref.current_user = db.get_user_by_id(u["id"])  # Обновляем объект пользователя
            self.accept()


class AdminPanelWidget(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        lbl = QLabel("⚙️ Панель разработчика (Admin)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 24px; color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(lbl)

        stats_box = QGroupBox("📊 Статистика системы")
        stats_box.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; color: black; }")
        stats_layout = QVBoxLayout()
        self.stats = QLabel("Загрузка статистики...")
        self.stats.setWordWrap(True)
        self.stats.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 20px;
                background-color: #34495e;
                color: white;
                border-radius: 8px;
                line-height: 1.8;
            }
        """)
        stats_layout.addWidget(self.stats)
        stats_box.setLayout(stats_layout)
        layout.addWidget(stats_box)

        grid = QGridLayout()
        grid.setSpacing(15)

        btn_add_game = self.create_admin_button("➕ Добавить игру", "#2ecc71")
        btn_edit_games = self.create_admin_button("✏️ Редактировать игры", "#3498db")
        btn_view_users = self.create_admin_button("👥 Просмотр пользователей", "#9b59b6")
        btn_reports = self.create_admin_button("📈 Отчёты", "#f39c12")

        grid.addWidget(btn_add_game, 0, 0)
        grid.addWidget(btn_edit_games, 0, 1)
        grid.addWidget(btn_view_users, 1, 0)
        grid.addWidget(btn_reports, 1, 1)

        layout.addLayout(grid)

        btn_back = QPushButton("⬅ Назад в меню")
        btn_back.setMinimumHeight(45)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        layout.addWidget(btn_back)

        btn_add_game.clicked.connect(self.add_game)
        btn_edit_games.clicked.connect(self.edit_games)
        btn_view_users.clicked.connect(self.view_users)
        btn_reports.clicked.connect(self.show_reports)
        btn_back.clicked.connect(lambda: self.app_ref.show_main_menu())

        self.setLayout(layout)
        self.refresh_stats()

    def create_admin_button(self, text, color):
        btn = QPushButton(text)
        btn.setMinimumHeight(80)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        return btn

    def refresh_stats(self):
        stats = db.get_statistics()
        self.stats.setText(f"""
        📈 <b>Общая статистика:</b><br>
        ━━━━━━━━━━━━━━━━━━━━━━━━<br>
        • <b>Активных подписок:</b> {stats['active_subscriptions']}<br>
        • <b>Всего пользователей:</b> {stats['total_users']}<br>
        • <b>Игр в каталоге:</b> {stats['total_games']}<br>
        • <b>Игр в подписке:</b> {stats['premium_games'] + stats['basic_games']}<br>
        • <b>Отдельных игр:</b> {stats['no_sub_games']}<br>
        • <b>Следующий ID игры:</b> {stats['next_game_id']}<br>
        • <b>Следующий ID пользователя:</b> {stats['next_user_id']}
        """)

    def add_game(self):
        dlg = GameAddDialog(self.app_ref)
        if dlg.exec():
            QMessageBox.information(self, "Успех", "Игра успешно добавлена в каталог.")
            self.refresh_stats()
            self.app_ref.refresh_data()

    def edit_games(self):
        dlg = GameEditListDialog(self.app_ref)
        dlg.exec()
        self.refresh_stats()
        self.app_ref.refresh_data()

    def view_users(self):
        dlg = UserListDialog(self.app_ref)
        dlg.exec()
        self.refresh_stats()
        self.app_ref.refresh_data()

    def show_reports(self):
        dlg = ReportsDialog(self.app_ref, self)
        dlg.exec()


class GameAddDialog(QDialog):
    def __init__(self, app_ref):
        super().__init__(app_ref)
        self.app_ref = app_ref
        self.setWindowTitle("➕ Добавление игры")
        self.resize(500, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("➕ Добавление новой игры")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 18px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(lbl)

        form_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Введите название игры")
        self.title_edit.setMinimumHeight(35)

        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("Например: RPG, Action, Strategy")
        self.genre_edit.setMinimumHeight(35)

        self.dev_edit = QLineEdit()
        self.dev_edit.setPlaceholderText("Название компании-разработчика")
        self.dev_edit.setMinimumHeight(35)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumHeight(35)

        self.price_spin = QSpinBox()
        self.price_spin.setRange(0, 100000)
        self.price_spin.setSuffix(" руб.")
        self.price_spin.setMinimumHeight(35)

        self.sub_combo = QComboBox()
        self.sub_combo.addItems(["Premium", "Basic", "Не доступна по подписке"])
        self.sub_combo.setMinimumHeight(35)

        self.desc = QTextEdit()
        self.desc.setPlaceholderText("Введите описание игры...")
        self.desc.setMinimumHeight(100)

        form_layout.addRow("Название игры:", self.title_edit)
        form_layout.addRow("Жанр:", self.genre_edit)
        form_layout.addRow("Разработчик:", self.dev_edit)
        form_layout.addRow("Дата выхода:", self.date_edit)
        form_layout.addRow("Доступна в подписке:", self.sub_combo)
        form_layout.addRow("Цена (руб):", self.price_spin)
        form_layout.addRow("Описание:", self.desc)

        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Сохранить")
        button_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
            }
        """)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
            }
        """)
        button_box.accepted.connect(self.save_game)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setStyleSheet("""
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333333;
                background-color: white;
            }
            QLabel {
                color: #333333;
            }
            QComboBox QAbstractItemView {
                color: #333333;
                background-color: white;
            }
            QCalendarWidget QWidget {
                color: #333333;
                background-color: white;
            }
        """)

        self.setLayout(layout)

    def save_game(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Ошибка", "Название игры обязательно.")
            return

        sub_text = self.sub_combo.currentText()
        if sub_text == "Premium":
            subscription_type = "premium"
        elif sub_text == "Basic":
            subscription_type = "basic"
        else:
            subscription_type = "none"

        game_data = {
            "title": title,
            "genre": self.genre_edit.text().strip(),
            "developer": self.dev_edit.text().strip(),
            "release_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "price": float(self.price_spin.value()),
            "subscription_type": subscription_type,
            "description": self.desc.toPlainText().strip()
        }

        game = db.create_game(game_data)
        if game:
            # Автоматически добавляем игру в библиотеки пользователей с соответствующими подписками
            if subscription_type != "none":
                users = db.get_all_users()
                for user in users:
                    subscription = db.get_user_subscription(user["id"])
                    if subscription:
                        plan = subscription["plan"]
                        if subscription_type == "basic" and plan in ["Basic", "Premium"]:
                            db.add_subscribed_game(user["id"], game["id"])
                        elif subscription_type == "premium" and plan == "Premium":
                            db.add_subscribed_game(user["id"], game["id"])
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить игру.")


class GameEditListDialog(QDialog):
    def __init__(self, app_ref):
        super().__init__(app_ref)
        self.app_ref = app_ref
        self.setWindowTitle("✏️ Редактирование игр")
        self.resize(900, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        lbl = QLabel("✏️ Редактирование игр")
        lbl.setStyleSheet("font-weight: bold; font-size: 18px; color: #2c3e50;")
        header_layout.addWidget(lbl)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Поиск по названию...")
        self.search_edit.setMinimumHeight(35)
        btn_search = QPushButton("Найти")
        btn_search.setMinimumHeight(35)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        header_layout.addWidget(self.search_edit)
        header_layout.addWidget(btn_search)
        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Жанр", "В подписке", "Цена", "Разработчик"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 13px;
                gridline-color: #ddd;
                background-color: white;
                color: #333333;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 6px;
                color: #333333;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_edit = QPushButton("✏️ Редактировать")
        btn_edit.setMinimumHeight(40)
        btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        btn_delete = QPushButton("🗑️ Удалить")
        btn_delete.setMinimumHeight(40)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        btn_close = QPushButton("Закрыть")
        btn_close.setMinimumHeight(40)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)

        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        btn_search.clicked.connect(self.search_games)
        btn_edit.clicked.connect(self.edit_selected)
        btn_delete.clicked.connect(self.delete_selected)
        btn_close.clicked.connect(self.reject)

        self.setLayout(layout)
        self.populate()

    def populate(self):
        games = db.get_all_games()
        self.table.setRowCount(len(games))

        for r, g in enumerate(games):
            self.table.setItem(r, 0, QTableWidgetItem(str(g["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(g["title"]))
            self.table.setItem(r, 2, QTableWidgetItem(g.get("genre", "")))

            sub_type = g.get("subscription_type", "none")
            if sub_type == "premium":
                sub_text = "✅ Premium"
            elif sub_type == "basic":
                sub_text = "✅ Basic"
            else:
                sub_text = "❌ Нет"

            self.table.setItem(r, 3, QTableWidgetItem(sub_text))
            self.table.setItem(r, 4, QTableWidgetItem(f"{g.get('price', 0)} руб."))
            self.table.setItem(r, 5, QTableWidgetItem(g.get("developer", "")))

    def search_games(self):
        search_text = self.search_edit.text().strip().lower()
        if not search_text:
            self.populate()
            return

        games = db.search_games(search_text)
        self.table.setRowCount(len(games))
        for r, g in enumerate(games):
            self.table.setItem(r, 0, QTableWidgetItem(str(g["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(g["title"]))
            self.table.setItem(r, 2, QTableWidgetItem(g.get("genre", "")))

            sub_type = g.get("subscription_type", "none")
            if sub_type == "premium":
                sub_text = "✅ Premium"
            elif sub_type == "basic":
                sub_text = "✅ Basic"
            else:
                sub_text = "❌ Нет"

            self.table.setItem(r, 3, QTableWidgetItem(sub_text))
            self.table.setItem(r, 4, QTableWidgetItem(f"{g.get('price', 0)} руб."))
            self.table.setItem(r, 5, QTableWidgetItem(g.get("developer", "")))

    def selected_game(self):
        sel = self.table.selectedItems()
        if not sel:
            return None
        gid = int(sel[0].text())
        return find_game_by_id(gid)

    def edit_selected(self):
        g = self.selected_game()
        if not g:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для редактирования.")
            return

        dlg = GameEditDialog(self.app_ref, game=g)
        if dlg.exec():
            QMessageBox.information(self, "Успех", "Игра успешно обновлена.")
            self.populate()

    def delete_selected(self):
        g = self.selected_game()
        if not g:
            QMessageBox.warning(self, "Ошибка", "Выберите игру для удаления.")
            return

        confirm = QMessageBox.warning(self, "Удаление игры",
                                      f"Вы уверены, что хотите удалить игру:\n\n<b>{g['title']}</b>?\n\nЭто действие необратимо.",
                                      QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            if db.delete_game(g["id"]):
                QMessageBox.information(self, "Успех", "Игра успешно удалена.")
                self.populate()


class GameEditDialog(QDialog):
    def __init__(self, app_ref, game=None):
        super().__init__(app_ref)
        self.app_ref = app_ref
        self.game = game
        self.setWindowTitle("✏️ Редактирование игры")
        self.resize(500, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("✏️ Редактирование игры")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 18px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(lbl)

        form_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Введите название игры")
        self.title_edit.setMinimumHeight(35)

        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("Например: RPG, Action, Strategy")
        self.genre_edit.setMinimumHeight(35)

        self.dev_edit = QLineEdit()
        self.dev_edit.setPlaceholderText("Название компании-разработчика")
        self.dev_edit.setMinimumHeight(35)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumHeight(35)

        self.price_spin = QSpinBox()
        self.price_spin.setRange(0, 100000)
        self.price_spin.setSuffix(" руб.")
        self.price_spin.setMinimumHeight(35)

        self.sub_combo = QComboBox()
        self.sub_combo.addItems(["Premium", "Basic", "Не доступна по подписке"])
        self.sub_combo.setMinimumHeight(35)

        self.desc = QTextEdit()
        self.desc.setPlaceholderText("Введите описание игры...")
        self.desc.setMinimumHeight(100)

        form_layout.addRow("Название игры:", self.title_edit)
        form_layout.addRow("Жанр:", self.genre_edit)
        form_layout.addRow("Разработчик:", self.dev_edit)
        form_layout.addRow("Дата выхода:", self.date_edit)
        form_layout.addRow("Доступна в подписке:", self.sub_combo)
        form_layout.addRow("Цена (руб):", self.price_spin)
        form_layout.addRow("Описание:", self.desc)

        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Сохранить")
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.accepted.connect(self.save_game)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setStyleSheet("""
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333333;
                background-color: white;
            }
            QLabel {
                color: #333333;
            }
            QComboBox QAbstractItemView {
                color: #333333;
                background-color: white;
            }
            QCalendarWidget QWidget {
                color: #333333;
                background-color: white;
            }
        """)

        self.setLayout(layout)

        if self.game:
            self.fill_from_game()

    def fill_from_game(self):
        g = self.game
        self.title_edit.setText(g["title"])
        self.genre_edit.setText(g.get("genre", ""))
        self.dev_edit.setText(g.get("developer", ""))
        try:
            d = date.fromisoformat(g.get("release_date"))
            self.date_edit.setDate(QDate(d.year, d.month, d.day))
        except:
            pass
        self.price_spin.setValue(int(g.get("price", 0)))

        sub_type = g.get("subscription_type", "none")
        if sub_type == "premium":
            self.sub_combo.setCurrentText("Premium")
        elif sub_type == "basic":
            self.sub_combo.setCurrentText("Basic")
        else:
            self.sub_combo.setCurrentText("Не доступна по подписке")

        self.desc.setPlainText(g.get("description", ""))

    def save_game(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Ошибка", "Название игры обязательно.")
            return

        sub_text = self.sub_combo.currentText()
        if sub_text == "Premium":
            subscription_type = "premium"
        elif sub_text == "Basic":
            subscription_type = "basic"
        else:
            subscription_type = "none"

        game_data = {
            "title": title,
            "genre": self.genre_edit.text().strip(),
            "developer": self.dev_edit.text().strip(),
            "release_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "price": float(self.price_spin.value()),
            "subscription_type": subscription_type,
            "description": self.desc.toPlainText().strip()
        }

        if db.update_game(self.game["id"], game_data):
            # Обновляем библиотеки пользователей
            if subscription_type == "none":
                # Удаляем игру из библиотек по подписке
                users = db.get_all_users()
                for user in users:
                    db.remove_subscribed_game(user["id"], self.game["id"])
            else:
                # Обновляем библиотеки в соответствии с новым типом подписки
                users = db.get_all_users()
                for user in users:
                    db.remove_subscribed_game(user["id"], self.game["id"])  # Сначала удаляем
                    subscription = db.get_user_subscription(user["id"])
                    if subscription:
                        plan = subscription["plan"]
                        if subscription_type == "basic" and plan in ["Basic", "Premium"]:
                            db.add_subscribed_game(user["id"], self.game["id"])
                        elif subscription_type == "premium" and plan == "Premium":
                            db.add_subscribed_game(user["id"], self.game["id"])
            self.accept()


class UserListDialog(QDialog):
    def __init__(self, app_ref):
        super().__init__(app_ref)
        self.app_ref = app_ref
        self.setWindowTitle("👥 Просмотр пользователей")
        self.resize(900, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        lbl = QLabel("👥 Просмотр пользователей")
        lbl.setStyleSheet("font-weight: bold; font-size: 18px; color: #2c3e50;")
        header_layout.addWidget(lbl)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Поиск по имени или email...")
        self.search_edit.setMinimumHeight(35)
        btn_search = QPushButton("Найти")
        btn_search.setMinimumHeight(35)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        header_layout.addWidget(self.search_edit)
        header_layout.addWidget(btn_search)
        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Имя пользователя", "Email", "Подписка", "Роль", "Дата регистрации"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 13px;
                gridline-color: #ddd;
                background-color: white;
                color: #333333;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 6px;
                color: #333333;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 120)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_view = QPushButton("👁️ Просмотр")
        btn_view.setMinimumHeight(40)
        btn_view.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        btn_role = QPushButton("👑 Изменить роль")
        btn_role.setMinimumHeight(40)
        btn_role.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)

        btn_delete = QPushButton("🗑️ Удалить")
        btn_delete.setMinimumHeight(40)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        btn_close = QPushButton("Закрыть")
        btn_close.setMinimumHeight(40)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)

        btn_layout.addWidget(btn_view)
        btn_layout.addWidget(btn_role)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        btn_search.clicked.connect(self.search_users)
        btn_view.clicked.connect(self.view_selected)
        btn_role.clicked.connect(self.change_role)
        btn_delete.clicked.connect(self.delete_selected)
        btn_close.clicked.connect(self.reject)

        self.setLayout(layout)
        self.populate()

    def populate(self):
        users = db.get_all_users()
        self.table.setRowCount(len(users))

        for r, u in enumerate(users):
            self.table.setItem(r, 0, QTableWidgetItem(str(u["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(u["username"]))
            self.table.setItem(r, 2, QTableWidgetItem(u.get("email", "")))

            sub = db.get_user_subscription(u["id"])
            sub_text = "—"
            if sub:
                days_left = (sub["end_date"] - date.today()).days
                sub_text = f"{sub['plan']} ({'активна' if days_left > 0 else 'истекла'})"

            self.table.setItem(r, 3, QTableWidgetItem(sub_text))

            role_text = "👑 Админ" if u.get("role") == "admin" else "👤 Пользователь"
            self.table.setItem(r, 4, QTableWidgetItem(role_text))
            self.table.setItem(r, 5, QTableWidgetItem(str(u.get("reg_date", ""))))

    def search_users(self):
        search_text = self.search_edit.text().strip().lower()
        if not search_text:
            self.populate()
            return

        users = db.get_all_users()
        filtered_users = []

        for u in users:
            if (search_text in u["username"].lower() or
                    search_text in u.get("email", "").lower() or
                    search_text in u.get("role", "").lower()):
                filtered_users.append(u)

        self.table.setRowCount(len(filtered_users))

        for r, u in enumerate(filtered_users):
            self.table.setItem(r, 0, QTableWidgetItem(str(u["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(u["username"]))
            self.table.setItem(r, 2, QTableWidgetItem(u.get("email", "")))

            sub = db.get_user_subscription(u["id"])
            sub_text = "—"
            if sub:
                days_left = (sub["end_date"] - date.today()).days
                sub_text = f"{sub['plan']} ({'активна' if days_left > 0 else 'истекла'})"

            self.table.setItem(r, 3, QTableWidgetItem(sub_text))

            role_text = "👑 Админ" if u.get("role") == "admin" else "👤 Пользователь"
            self.table.setItem(r, 4, QTableWidgetItem(role_text))
            self.table.setItem(r, 5, QTableWidgetItem(str(u.get("reg_date", ""))))

    def selected_user(self):
        sel = self.table.selectedItems()
        if not sel:
            return None
        uid = int(sel[0].text())
        return find_user_by_id(uid)

    def view_selected(self):
        u = self.selected_user()
        if not u:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя.")
            return

        sub = db.get_user_subscription(u["id"])
        sub_text = "Нет активной подписки"
        if sub:
            days_left = (sub["end_date"] - date.today()).days
            sub_text = f"{sub['plan']} (до {sub['end_date']}, осталось {days_left} дней)"

        library = get_user_library(u)
        purchased_count = len(db.get_user_purchased_games(u["id"]))
        subscribed_count = len(db.get_user_subscribed_games(u["id"]))

        text = f"""
        <b style="color: #333333;">👤 Информация о пользователе</b><br>
        ━━━━━━━━━━━━━━━━━━━━━━━━<br><br>
        <b style="color: #333333;">ID:</b> {u['id']}<br>
        <b style="color: #333333;">Имя пользователя:</b> {u['username']}<br>
        <b style="color: #333333;">Email:</b> {u['email']}<br>
        <b style="color: #333333;">Роль:</b> {u['role']}<br>
        <b style="color: #333333;">Дата регистрации:</b> {u['reg_date']}<br>
        <b style="color: #333333;">Подписка:</b> {sub_text}<br>
        <b style="color: #333333;">Игр в библиотеке:</b> {len(library)}<br>
        <b style="color: #333333;">Купленных игр:</b> {purchased_count}<br>
        <b style="color: #333333;">Игр по подписке:</b> {subscribed_count}
        """

        QMessageBox.information(self, "Информация о пользователе", text)

    def change_role(self):
        u = self.selected_user()
        if not u:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя.")
            return

        if u["id"] == self.app_ref.current_user["id"]:
            QMessageBox.warning(self, "Ошибка", "Нельзя изменить свою собственную роль.")
            return

        current_role = u.get("role", "user")
        new_role = "admin" if current_role == "user" else "user"

        confirm = QMessageBox.question(self, "Изменение роли",
                                       f"Изменить роль пользователя '{u['username']}' с '{current_role}' на '{new_role}'?",
                                       QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            if db.update_user_role(u["id"], new_role):
                QMessageBox.information(self, "Успех", f"Роль пользователя '{u['username']}' изменена на '{new_role}'.")
                self.populate()

    def delete_selected(self):
        u = self.selected_user()
        if not u:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя.")
            return

        if u["id"] == self.app_ref.current_user["id"]:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить свой собственный аккаунт.")
            return

        confirm = QMessageBox.warning(self, "Удаление пользователя",
                                      f"Вы уверены, что хотите удалить пользователя:\n\n<b>{u['username']}</b>?\n\nЭто действие необратимо.",
                                      QMessageBox.Yes | QMessageBox.No)

        if confirm == QMessageBox.Yes:
            if db.delete_user(u["id"]):
                QMessageBox.information(self, "Успех", f"Пользователь '{u['username']}' успешно удалён.")
                self.populate()


class ReportsDialog(QDialog):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.setWindowTitle("📈 Отчёты системы")
        self.resize(700, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("📈 Отчёты системы")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 20px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(lbl)

        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
            QTabBar::tab {
                padding: 10px;
                margin-right: 5px;
                background-color: #ecf0f1;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        stats_tab = QWidget()
        stats_layout = QVBoxLayout()

        stats_text = QTextEdit()
        stats_text.setReadOnly(True)
        stats_text.setHtml(self.generate_general_stats())
        stats_layout.addWidget(stats_text)

        stats_tab.setLayout(stats_layout)
        tab_widget.addTab(stats_tab, "📊 Общая статистика")

        games_tab = QWidget()
        games_layout = QVBoxLayout()

        games_text = QTextEdit()
        games_text.setReadOnly(True)
        games_text.setHtml(self.generate_games_stats())
        games_layout.addWidget(games_text)

        games_tab.setLayout(games_layout)
        tab_widget.addTab(games_tab, "🎮 Статистика по играм")

        users_tab = QWidget()
        users_layout = QVBoxLayout()

        users_text = QTextEdit()
        users_text.setReadOnly(True)
        users_text.setHtml(self.generate_users_stats())
        users_layout.addWidget(users_text)

        users_tab.setLayout(users_layout)
        tab_widget.addTab(users_tab, "👥 Статистика по пользователям")

        finance_tab = QWidget()
        finance_layout = QVBoxLayout()

        finance_text = QTextEdit()
        finance_text.setReadOnly(True)
        finance_text.setHtml(self.generate_finance_stats())
        finance_layout.addWidget(finance_text)

        finance_tab.setLayout(finance_layout)
        tab_widget.addTab(finance_tab, "💰 Финансовая статистика")

        layout.addWidget(tab_widget)

        btn_close = QPushButton("Закрыть")
        btn_close.setMinimumHeight(40)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.setLayout(layout)

    def generate_general_stats(self):
        stats = db.get_statistics()

        return f"""
        <h2>📊 Общая статистика системы</h2>
        <hr>
        <h3>👥 Пользователи:</h3>
        <ul>
            <li><b>Всего пользователей:</b> {stats['total_users']}</li>
            <li><b>Администраторов:</b> {stats['admin_users']}</li>
            <li><b>Обычных пользователей:</b> {stats['regular_users']}</li>
            <li><b>Пользователей с активной подпиской:</b> {stats['active_subscriptions']} ({round(stats['active_subscriptions'] / stats['total_users'] * 100 if stats['total_users'] else 0, 1)}%)</li>
        </ul>

        <h3>💰 Подписки:</h3>
        <ul>
            <li><b>Всего активных подписок:</b> {stats['active_subscriptions']}</li>
            <li><b>Premium подписок:</b> {stats['premium_subscriptions']}</li>
            <li><b>Basic подписок:</b> {stats['basic_subscriptions']}</li>
        </ul>

        <h3>🎮 Игры:</h3>
        <ul>
            <li><b>Всего игр в каталоге:</b> {stats['total_games']}</li>
            <li><b>Игр в подписке:</b> {stats['premium_games'] + stats['basic_games']}</li>
            <li><b>Отдельно продаваемых игр:</b> {stats['no_sub_games']}</li>
        </ul>

        <h3>📅 Даты:</h3>
        <ul>
            <li><b>Следующий ID пользователя:</b> {stats['next_user_id']}</li>
            <li><b>Следующий ID игры:</b> {stats['next_game_id']}</li>
        </ul>
        """

    def generate_games_stats(self):
        games = db.get_all_games()

        if not games:
            return "<h2>🎮 Статистика по играм</h2><hr><p>В каталоге нет игр.</p>"

        genres = {}
        for g in games:
            genre = g.get("genre", "Не указан")
            genres[genre] = genres.get(genre, 0) + 1

        genres_html = "<ul>"
        for genre, count in sorted(genres.items(), key=lambda x: x[1], reverse=True):
            percentage = round(count / len(games) * 100, 1)
            genres_html += f"<li><b>{genre}:</b> {count} игр ({percentage}%)</li>"
        genres_html += "</ul>"

        expensive_games = sorted(games, key=lambda x: x.get("price", 0), reverse=True)[:5]
        expensive_html = "<ul>"
        for g in expensive_games:
            expensive_html += f"<li><b>{g['title']}:</b> {g.get('price', 0)} руб.</li>"
        expensive_html += "</ul>"

        stats = db.get_statistics()
        premium_games = stats['premium_games']
        basic_games = stats['basic_games']
        no_sub_games = stats['no_sub_games']

        return f"""
        <h2>🎮 Статистика по играм</h2>
        <hr>
        <h3>📊 Распределение по жанрам:</h3>
        {genres_html}

        <h3>💰 Доступность в подписке:</h3>
        <ul>
            <li><b>Доступны по Premium подписке:</b> {premium_games} игр ({round(premium_games / len(games) * 100, 1)}%)</li>
            <li><b>Доступны по Basic подписке:</b> {basic_games} игр ({round(basic_games / len(games) * 100, 1)}%)</li>
            <li><b>Только покупка:</b> {no_sub_games} игр ({round(no_sub_games / len(games) * 100, 1)}%)</li>
        </ul>

        <h3>🏆 Самые дорогие игры:</h3>
        {expensive_html}

        <h3>📈 Ценовая статистика:</h3>
        <ul>
            <li><b>Средняя цена игры:</b> {sum(float(g.get('price', 0)) for g in games) / len(games):.0f} руб.</li>
            <li><b>Минимальная цена:</b> {min(float(g.get('price', 0)) for g in games):.0f} руб.</li>
            <li><b>Максимальная цена:</b> {max(float(g.get('price', 0)) for g in games):.0f} руб.</li>
            <li><b>Общая стоимость каталога:</b> {sum(float(g.get('price', 0)) for g in games):.0f} руб.</li>
        </ul>
        """

    def generate_users_stats(self):
        users = db.get_all_users()

        if not users:
            return "<h2>👥 Статистика по пользователям</h2><hr><p>В системе нет пользователей.</p>"

        users_with_sub = [u for u in users if db.get_user_subscription(u["id"])]
        users_without_sub = len(users) - len(users_with_sub)

        avg_library_size = sum(len(get_user_library(u)) for u in users) / len(users)

        users_sorted = sorted(users, key=lambda x: len(get_user_library(x)), reverse=True)[:5]
        top_users_html = "<ul>"
        for u in users_sorted:
            top_users_html += f"<li><b>{u['username']}:</b> {len(get_user_library(u))} игр</li>"
        top_users_html += "</ul>"

        stats = db.get_statistics()

        return f"""
        <h2>👥 Статистика по пользователям</h2>
        <hr>
        <h3>📊 Общая информация:</h3>
        <ul>
            <li><b>Всего пользователей:</b> {len(users)}</li>
            <li><b>С подпиской:</b> {len(users_with_sub)} ({round(len(users_with_sub) / len(users) * 100, 1)}%)</li>
            <li><b>Без подписки:</b> {users_without_sub} ({round(users_without_sub / len(users) * 100, 1)}%)</li>
            <li><b>Средний размер библиотеки:</b> {avg_library_size:.1f} игр</li>
        </ul>

        <h3>🎮 Топ пользователей по размеру библиотеки:</h3>
        {top_users_html}

        <h3>💰 Типы подписок:</h3>
        <ul>
            <li><b>Premium подписок:</b> {stats['premium_subscriptions']}</li>
            <li><b>Basic подписок:</b> {stats['basic_subscriptions']}</li>
        </ul>

        <h3>📅 Регистрации по датам:</h3>
        <ul>
            <li><b>Последняя регистрация:</b> {max(u.get('reg_date', '') for u in users)}</li>
            <li><b>Первая регистрация:</b> {min(u.get('reg_date', '') for u in users)}</li>
        </ul>
        """

    def generate_finance_stats(self):
        games = db.get_all_games()
        users = db.get_all_users()

        monthly_sub_income = 0.0
        for u in users:
            sub = db.get_user_subscription(u["id"])
            if sub:
                plan = sub.get("plan")
                if plan == "Premium":
                    monthly_sub_income += 699.0 / 3.0  # 90 дней за 699 руб = ~233 руб/мес
                elif plan == "Basic":
                    monthly_sub_income += 299.0  # 30 дней за 299 руб

        # Преобразуем Decimal в float для вычислений
        potential_game_income = sum(float(g.get("price", 0)) for g in games if g.get("subscription_type") == "none")
        sub_games_value = sum(float(g.get("price", 0)) for g in games if g.get("subscription_type") != "none")
        total_catalog_value = sum(float(g.get("price", 0)) for g in games)

        # Проверяем деление на ноль
        ratio = 0.0
        if monthly_sub_income * 12 > 0:
            ratio = sub_games_value / (monthly_sub_income * 12)

        # Проверяем наличие игр для корректного вычисления средних значений
        games_for_sale = [g for g in games if g.get("subscription_type") == "none"]
        games_in_sub = [g for g in games if g.get("subscription_type") != "none"]

        avg_sale_price = 0.0
        if games_for_sale:
            avg_sale_price = sum(float(g.get("price", 0)) for g in games_for_sale) / len(games_for_sale)

        avg_sub_price = 0.0
        if games_in_sub:
            avg_sub_price = sum(float(g.get("price", 0)) for g in games_in_sub) / len(games_in_sub)

        avg_price = 0.0
        if games:
            avg_price = total_catalog_value / len(games)

        avg_income_per_user = 0.0
        if users:
            avg_income_per_user = monthly_sub_income / len(users)

        return f"""
        <h2>💰 Финансовая статистика</h2>
        <hr>
        <h3>💵 Доход от подписок:</h3>
        <ul>
            <li><b>Месячный доход от подписок:</b> {monthly_sub_income:.0f} руб.</li>
            <li><b>Годовой доход от подписок:</b> {monthly_sub_income * 12:.0f} руб.</li>
            <li><b>Средний доход на пользователя:</b> {avg_income_per_user:.0f} руб./мес</li>
        </ul>

        <h3>🎮 Потенциальный доход от продаж игр:</h3>
        <ul>
            <li><b>Общая стоимость игр для продажи:</b> {potential_game_income:.0f} руб.</li>
            <li><b>Средняя цена продаваемой игры:</b> {avg_sale_price:.0f} руб.</li>
        </ul>

        <h3>📊 Стоимость контента в подписке:</h3>
        <ul>
            <li><b>Общая стоимость игр в подписке:</b> {sub_games_value:.0f} руб.</li>
            <li><b>Средняя стоимость игры в подписке:</b> {avg_sub_price:.0f} руб.</li>
            <li><b>Соотношение стоимости подписки к стоимости игр:</b> 1:{ratio:.1f}</li>
        </ul>

        <h3>📈 Экономические показатели:</h3>
        <ul>
            <li><b>Общая стоимость каталога:</b> {total_catalog_value:.0f} руб.</li>
            <li><b>Средняя цена игры в каталоге:</b> {avg_price:.0f} руб.</li>
            <li><b>Процент игр в подписке:</b> {len(games_in_sub) / len(games) * 100 if games else 0:.1f}%</li>
        </ul>
        """


# -----------------------------
# Главное окно приложения
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎮 Game Subscription Service с PostgreSQL")
        self.resize(1000, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
        """)

        # Текущий пользователь
        self.current_user = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Создание экранов
        self.login = LoginWidget(self)
        self.register = RegisterWidget(self)
        self.main_menu = MainMenuWidget(self)
        self.catalog = CatalogWidget(self)
        self.library = LibraryWidget(self)
        self.subscription = SubscriptionWidget(self)
        self.profile = ProfileWidget(self)
        self.admin_panel = AdminPanelWidget(self)

        # Добавление в стек
        for w in (self.login, self.register, self.main_menu, self.catalog,
                  self.library, self.subscription, self.profile, self.admin_panel):
            self.stack.addWidget(w)

        self.show_login()

    def refresh_data(self):
        """Метод для обновления данных пользователя после изменений"""
        if self.current_user:
            self.current_user = db.get_user_by_id(self.current_user["id"])

    # Навигация
    def show_login(self):
        self.stack.setCurrentWidget(self.login)

    def show_register(self):
        self.stack.setCurrentWidget(self.register)

    def show_main_menu(self):
        self.main_menu.refresh()
        self.stack.setCurrentWidget(self.main_menu)

    def show_catalog(self):
        self.catalog.populate()
        self.stack.setCurrentWidget(self.catalog)

    def show_library(self):
        self.library.refresh()
        self.stack.setCurrentWidget(self.library)

    def show_subscription(self):
        self.subscription.refresh()
        self.stack.setCurrentWidget(self.subscription)

    def show_profile(self):
        self.profile.refresh()
        self.stack.setCurrentWidget(self.profile)

    def show_admin_panel(self):
        if not self.current_user or self.current_user.get("role") != "admin":
            QMessageBox.warning(self, "Доступ запрещён", "Эта панель доступна только администраторам.")
            return
        self.admin_panel.refresh_stats()
        self.stack.setCurrentWidget(self.admin_panel)


# -----------------------------
# Запуск приложения
# -----------------------------
def main():
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #333333;
        }

        QPushButton {
            font-size: 14px;
            padding: 8px 15px;
            border-radius: 4px;
        }

        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            color: #333333;
            background-color: white;
        }

        QLineEdit:focus, QTextEdit:focus {
            border-color: #3498db;
        }

        QGroupBox {
            font-weight: bold;
            border: 2px solid #ddd;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            color: #333333;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #333333;
        }

        QTableWidget {
            alternate-background-color: #f8f9fa;
            selection-background-color: #3498db;
            selection-color: white;
            color: #333333;
        }

        QDialog {
            background-color: white;
        }

        QMessageBox {
            background-color: white;
            color: #333333;
        }

        QLabel {
            color: #333333;
        }

        QComboBox QAbstractItemView {
            color: #333333;
            background-color: white;
        }

        QCalendarWidget QWidget {
            color: #333333;
            background-color: white;
        }
    """)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # Проверяем подключение к БД перед запуском
    try:
        # Простой тест подключения
        db.get_all_users()
        print("Подключение к PostgreSQL успешно установлено")
    except Exception as e:
        print(f"Ошибка подключения к PostgreSQL: {e}")
        print("Проверьте настройки в файле .env")
        sys.exit(1)

    main()