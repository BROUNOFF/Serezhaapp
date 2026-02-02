# config.py
import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Конфигурация подключения к базе данных PostgreSQL"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: str = os.getenv("DB_PORT", "5432")
    database: str = os.getenv("DB_NAME", "game_subs_db")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "password")

    @property
    def connection_string(self) -> str:
        """Возвращает строку подключения"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def psycopg2_params(self) -> dict:
        """Возвращает параметры для psycopg2"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password
        }


# Создаем экземпляр конфигурации
db_config = DatabaseConfig()