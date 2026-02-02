# init_db.py
import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Основная функция инициализации"""
    try:
        logger.info("Начало инициализации базы данных...")

        # Проверяем, есть ли уже данные в базе
        users = db.get_all_users()
        games = db.get_all_games()

        if not users:
            logger.info("Создание тестовых данных...")
            db.create_sample_data()
            logger.info("Тестовые данные успешно созданы")
        else:
            logger.info(f"В базе уже есть {len(users)} пользователей и {len(games)} игр")

        # Выводим статистику
        stats = db.get_statistics()
        logger.info(f"Статистика системы:")
        logger.info(f"  Пользователей: {stats['total_users']}")
        logger.info(f"  Игр в каталоге: {stats['total_games']}")
        logger.info(f"  Активных подписок: {stats['active_subscriptions']}")

        logger.info("Инициализация базы данных завершена успешно!")

    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()