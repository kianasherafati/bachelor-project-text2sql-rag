import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


def main():
    # Load configuration only when this script is executed directly.
    env_path = Path(__file__).with_name(".env")
    load_dotenv(env_path)

    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")
    driver = os.getenv(
        "DB_DRIVER",
        "ODBC Driver 17 for SQL Server"
    )
    auth = os.getenv("DB_AUTH", "windows")

    if not server:
        raise ValueError("DB_SERVER is missing from .env")

    if not database:
        raise ValueError("DB_DATABASE is missing from .env")

    if auth == "windows":
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )

    elif auth == "sql":
        username = os.getenv("DB_USERNAME")
        password = os.getenv("DB_PASSWORD")

        if not username or not password:
            raise ValueError(
                "DB_USERNAME and DB_PASSWORD are required "
                "for SQL authentication."
            )

        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    else:
        raise ValueError(
            "DB_AUTH must be either 'windows' or 'sql'."
        )

    with pyodbc.connect(
        connection_string,
        timeout=5
    ) as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                DB_NAME() AS DatabaseName,
                @@SERVERNAME AS ServerName,
                @@VERSION AS Version
        """)

        row = cursor.fetchone()

        print("Connection successful.")
        print("Database:", row.DatabaseName)
        print("Server:", row.ServerName)
        print("Version:")
        print(row.Version)


if __name__ == "__main__":
    main()
