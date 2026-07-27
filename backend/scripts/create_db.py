"""Crea la base de datos MySQL si no existe (usa variables de .env)."""

import pymysql
from app.config.settings import get_settings


def main() -> None:
    s = get_settings()
    conn = pymysql.connect(
        host=s.mysql_host,
        port=s.mysql_port,
        user=s.mysql_user,
        password=s.mysql_password,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{s.mysql_database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"Base de datos '{s.mysql_database}' lista.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
