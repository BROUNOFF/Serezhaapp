# database.py
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import pool
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import hashlib
from contextlib import contextmanager
import logging

from config import db_config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных PostgreSQL"""

    def __init__(self, min_connections=1, max_connections=10):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_pool = None
        self._init_pool()
        self._init_database()

    def _init_pool(self):
        """Инициализация пула соединений"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                self.min_connections,
                self.max_connections,
                **db_config.psycopg2_params
            )
            logger.info("Пул соединений с PostgreSQL успешно создан")
        except Exception as e:
            logger.error(f"Ошибка при создании пула соединений: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для получения соединения из пула"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Ошибка при работе с соединением: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    @contextmanager
    def get_cursor(self, conn=None):
        """Контекстный менеджер для получения курсора"""
        close_conn = False
        if not conn:
            conn = self.connection_pool.getconn()
            close_conn = True

        cursor = None
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при работе с курсором: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if close_conn and conn:
                self.connection_pool.putconn(conn)

    def _init_database(self):
        """Инициализация базы данных (создание таблиц при необходимости)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Проверяем существование таблиц
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        password_hash VARCHAR(64) NOT NULL,
                        role VARCHAR(10) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
                        reg_date DATE DEFAULT CURRENT_DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS games (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(100) NOT NULL,
                        genre VARCHAR(50),
                        description TEXT,
                        developer VARCHAR(100),
                        release_date DATE,
                        subscription_type VARCHAR(10) DEFAULT 'none' 
                            CHECK (subscription_type IN ('none', 'basic', 'premium')),
                        price DECIMAL(10, 2) DEFAULT 0.00,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        plan VARCHAR(10) CHECK (plan IN ('Basic', 'Premium')),
                        start_date DATE DEFAULT CURRENT_DATE,
                        end_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id)
                    );
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_purchased_games (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
                        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, game_id)
                    );
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_subscribed_games (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, game_id)
                    );
                """)

                # Создаем индексы для ускорения поиска
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_title ON games(title);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_genre ON games(genre);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_end_date ON subscriptions(end_date);")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_purchased_games_user ON user_purchased_games(user_id);")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_subscribed_games_user ON user_subscribed_games(user_id);")

                conn.commit()
                logger.info("Таблицы базы данных успешно созданы/проверены")

    # Методы для работы с пользователями

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Получить пользователя по имени"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE LOWER(username) = LOWER(%s)",
                (username,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получить пользователя по ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    def create_user(self, username: str, email: str, password: str, role: str = "user") -> Optional[Dict]:
        """Создать нового пользователя"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        with self.get_cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role, reg_date)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (username, email, password_hash, role, date.today()))

                result = cursor.fetchone()
                return dict(result) if result else None
            except psycopg2.IntegrityError as e:
                logger.error(f"Ошибка при создании пользователя: {e}")
                return None

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Обновить пароль пользователя"""
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()

        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (password_hash, user_id)
            )
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """Удалить пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return cursor.rowcount > 0

    def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]

    def update_user_role(self, user_id: int, role: str) -> bool:
        """Обновить роль пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET role = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (role, user_id)
            )
            return cursor.rowcount > 0

    # Методы для работы с играми

    def get_all_games(self) -> List[Dict]:
        """Получить все игры"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM games ORDER BY title")
            return [dict(row) for row in cursor.fetchall()]

    def get_game_by_id(self, game_id: int) -> Optional[Dict]:
        """Получить игру по ID"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM games WHERE id = %s", (game_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    def create_game(self, game_data: Dict) -> Optional[Dict]:
        """Создать новую игру"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO games (title, genre, description, developer, release_date, subscription_type, price)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                game_data.get("title"),
                game_data.get("genre", ""),
                game_data.get("description", ""),
                game_data.get("developer", ""),
                game_data.get("release_date"),
                game_data.get("subscription_type", "none"),
                game_data.get("price", 0.0)
            ))

            result = cursor.fetchone()
            return dict(result) if result else None

    def update_game(self, game_id: int, game_data: Dict) -> bool:
        """Обновить информацию об игре"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE games 
                SET title = %s, genre = %s, description = %s, developer = %s, 
                    release_date = %s, subscription_type = %s, price = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                game_data.get("title"),
                game_data.get("genre", ""),
                game_data.get("description", ""),
                game_data.get("developer", ""),
                game_data.get("release_date"),
                game_data.get("subscription_type", "none"),
                game_data.get("price", 0.0),
                game_id
            ))
            return cursor.rowcount > 0

    def delete_game(self, game_id: int) -> bool:
        """Удалить игру"""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM games WHERE id = %s", (game_id,))
            return cursor.rowcount > 0

    def search_games(self, query: str) -> List[Dict]:
        """Поиск игр по названию, жанру или описанию"""
        with self.get_cursor() as cursor:
            search_term = f"%{query}%"
            cursor.execute("""
                SELECT * FROM games 
                WHERE title ILIKE %s OR genre ILIKE %s OR description ILIKE %s
                ORDER BY title
            """, (search_term, search_term, search_term))
            return [dict(row) for row in cursor.fetchall()]

    # Методы для работы с подписками

    def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """Получить подписку пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM subscriptions WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    def create_or_update_subscription(self, user_id: int, plan: str, end_date: date) -> Optional[Dict]:
        """Создать или обновить подписку пользователя"""
        with self.get_cursor() as cursor:
            # Проверяем существующую подписку
            cursor.execute("SELECT * FROM subscriptions WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()

            if existing:
                # Обновляем существующую подписку
                cursor.execute("""
                    UPDATE subscriptions 
                    SET plan = %s, end_date = %s, created_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    RETURNING *
                """, (plan, end_date, user_id))
            else:
                # Создаем новую подписку
                cursor.execute("""
                    INSERT INTO subscriptions (user_id, plan, end_date)
                    VALUES (%s, %s, %s)
                    RETURNING *
                """, (user_id, plan, end_date))

            result = cursor.fetchone()
            return dict(result) if result else None

    def cancel_subscription(self, user_id: int) -> bool:
        """Отменить подписку пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM subscriptions WHERE user_id = %s", (user_id,))
            return cursor.rowcount > 0

    def extend_subscription(self, user_id: int, additional_days: int) -> Optional[Dict]:
        """Продлить подписку на указанное количество дней"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE subscriptions 
                SET end_date = end_date + INTERVAL '%s days'
                WHERE user_id = %s
                RETURNING *
            """, (additional_days, user_id))

            result = cursor.fetchone()
            return dict(result) if result else None

    # Методы для работы с библиотекой пользователя

    def get_user_purchased_games(self, user_id: int) -> List[int]:
        """Получить список ID купленных игр пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT game_id FROM user_purchased_games WHERE user_id = %s",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def get_user_subscribed_games(self, user_id: int) -> List[int]:
        """Получить список ID игр по подписке пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT game_id FROM user_subscribed_games WHERE user_id = %s",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def add_purchased_game(self, user_id: int, game_id: int) -> bool:
        """Добавить купленную игру пользователю"""
        with self.get_cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO user_purchased_games (user_id, game_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, game_id) DO NOTHING
                """, (user_id, game_id))
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Ошибка при добавлении купленной игры: {e}")
                return False

    def add_subscribed_game(self, user_id: int, game_id: int) -> bool:
        """Добавить игру по подписке пользователю"""
        with self.get_cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO user_subscribed_games (user_id, game_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, game_id) DO NOTHING
                """, (user_id, game_id))
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Ошибка при добавлении игры по подписке: {e}")
                return False

    def remove_purchased_game(self, user_id: int, game_id: int) -> bool:
        """Удалить купленную игру из библиотеки пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_purchased_games WHERE user_id = %s AND game_id = %s",
                (user_id, game_id)
            )
            return cursor.rowcount > 0

    def remove_subscribed_game(self, user_id: int, game_id: int) -> bool:
        """Удалить игру по подписке из библиотеки пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_subscribed_games WHERE user_id = %s AND game_id = %s",
                (user_id, game_id)
            )
            return cursor.rowcount > 0

    def clear_subscribed_games(self, user_id: int) -> bool:
        """Очистить все игры по подписке у пользователя"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_subscribed_games WHERE user_id = %s",
                (user_id,)
            )
            return cursor.rowcount > 0

    # Методы для статистики и отчетов

    def get_statistics(self) -> Dict:
        """Получить статистику системы"""
        with self.get_cursor() as cursor:
            stats = {}

            # Общее количество пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            stats["total_users"] = cursor.fetchone()[0]

            # Количество администраторов
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            stats["admin_users"] = cursor.fetchone()[0]

            # Количество обычных пользователей
            stats["regular_users"] = stats["total_users"] - stats["admin_users"]

            # Количество активных подписок
            cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE end_date >= CURRENT_DATE")
            stats["active_subscriptions"] = cursor.fetchone()[0]

            # Количество подписок Premium и Basic
            cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE plan = 'Premium' AND end_date >= CURRENT_DATE")
            stats["premium_subscriptions"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE plan = 'Basic' AND end_date >= CURRENT_DATE")
            stats["basic_subscriptions"] = cursor.fetchone()[0]

            # Общее количество игр
            cursor.execute("SELECT COUNT(*) FROM games")
            stats["total_games"] = cursor.fetchone()[0]

            # Игры по типам подписки
            cursor.execute("SELECT COUNT(*) FROM games WHERE subscription_type = 'premium'")
            stats["premium_games"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM games WHERE subscription_type = 'basic'")
            stats["basic_games"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM games WHERE subscription_type = 'none'")
            stats["no_sub_games"] = cursor.fetchone()[0]

            # Следующий ID пользователя и игры
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM users")
            stats["next_user_id"] = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM games")
            stats["next_game_id"] = cursor.fetchone()[0]

            return stats

    # Вспомогательные методы для обратной совместимости

    def get_all_data(self) -> Dict:
        """Получить все данные системы в формате, аналогичном JSON"""
        data = {}

        # Получаем статистику для next_user_id и next_game_id
        stats = self.get_statistics()
        data["next_user_id"] = stats["next_user_id"]
        data["next_game_id"] = stats["next_game_id"]

        # Получаем всех пользователей
        users = []
        for user in self.get_all_users():
            user_dict = dict(user)

            # Получаем подписку пользователя
            subscription = self.get_user_subscription(user_dict["id"])
            if subscription:
                user_dict["subscription"] = {
                    "plan": subscription["plan"],
                    "end_date": subscription["end_date"].isoformat()
                }
            else:
                user_dict["subscription"] = None

            # Получаем игры пользователя
            user_dict["purchased_games"] = self.get_user_purchased_games(user_dict["id"])
            user_dict["subscribed_games"] = self.get_user_subscribed_games(user_dict["id"])
            user_dict["library"] = []  # Для обратной совместимости

            # Конвертируем даты в строки
            if user_dict["reg_date"]:
                user_dict["reg_date"] = user_dict["reg_date"].isoformat()

            users.append(user_dict)

        data["users"] = users

        # Получаем все игры
        games = []
        for game in self.get_all_games():
            game_dict = dict(game)

            # Конвертируем даты в строки
            if game_dict["release_date"]:
                game_dict["release_date"] = game_dict["release_date"].isoformat()

            # Конвертируем Decimal в float для совместимости с JSON
            if game_dict["price"]:
                game_dict["price"] = float(game_dict["price"])

            games.append(game_dict)

        data["games"] = games

        return data

    def create_sample_data(self):
        """Создать тестовые данные"""
        today = date.today()

        # Создаем тестовых пользователей
        admin = self.create_user(
            username="admin",
            email="admin@mail.com",
            password="admin123",
            role="admin"
        )

        gamer = self.create_user(
            username="gamer01",
            email="gamer@mail.com",
            password="password",
            role="user"
        )

        # Создаем подписки
        if admin:
            self.create_or_update_subscription(
                admin["id"],
                "Premium",
                today + timedelta(days=60)
            )

        if gamer:
            self.create_or_update_subscription(
                gamer["id"],
                "Basic",
                today + timedelta(days=10)
            )

        # Создаем игры
        games_data = [
            {
                "title": "GTA V",
                "genre": "Action",
                "description": "Open-world action game with extensive gameplay.",
                "developer": "Rockstar",
                "release_date": "2013-09-17",
                "subscription_type": "basic",
                "price": 499.0
            },
            {
                "title": "Witcher 3",
                "genre": "RPG",
                "description": "Story-rich RPG with deep characters and world.",
                "developer": "CD Projekt",
                "release_date": "2015-05-19",
                "subscription_type": "none",
                "price": 1299.0
            },
            {
                "title": "Minecraft",
                "genre": "Sandbox",
                "description": "Creative sandbox building game.",
                "developer": "Mojang",
                "release_date": "2011-11-18",
                "subscription_type": "basic",
                "price": 1199.0
            },
        ]

        created_games = []
        for game_data in games_data:
            game = self.create_game(game_data)
            if game:
                created_games.append(game)

        # Добавляем игры в библиотеки пользователей
        if admin and created_games:
            self.add_subscribed_game(admin["id"], created_games[0]["id"])
            self.add_subscribed_game(admin["id"], created_games[2]["id"])

        if gamer and len(created_games) >= 3:
            self.add_subscribed_game(gamer["id"], created_games[2]["id"])
            self.add_purchased_game(gamer["id"], created_games[1]["id"])

        logger.info("Тестовые данные успешно созданы")


# Создаем глобальный экземпляр базы данных
db = Database()