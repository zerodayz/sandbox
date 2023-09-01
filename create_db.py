import sqlite3

import utils.constants as constants

DB_NAME = constants.DB_NAME


def create_tables_and_triggers():
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.cursor()

        create_table_users_query = """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY NOT NULL,
                password TEXT NOT NULL,
                team INTEGER DEFAULT NULL,
                team_invitation INTEGER DEFAULT NULL
            );
        """

        create_table_scores_query = """
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                exercise_id INTEGER NOT NULL,
                total_score INTEGER NOT NULL,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """

        create_table_teams_query = """
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                owner TEXT NOT NULL,
                logo BLOB DEFAULT NULL,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """

        create_table_exercise_query = """
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                sample_1_input TEXT,
                sample_1_output BLOB,
                sample_2_input TEXT,
                sample_2_output BLOB,
                sample_3_input TEXT,
                sample_3_output BLOB,
                code TEXT,
                language TEXT,
                difficulty TEXT,
                added_by TEXT,
                score INTEGER
            );
        """

        create_table_scores_trigger_1 = """
            CREATE TRIGGER IF NOT EXISTS set_date_created_insert
            AFTER INSERT ON scores
            BEGIN
                UPDATE scores
                SET date_created = datetime('now')
                WHERE id = NEW.id;
            END;
        """

        create_table_scores_trigger_2 = """
            CREATE TRIGGER IF NOT EXISTS set_date_created_update
            AFTER UPDATE ON scores
            BEGIN
                UPDATE scores
                SET date_created = datetime('now')
                WHERE id = NEW.id;
            END;
        """

        cursor.execute(create_table_users_query)
        cursor.execute(create_table_scores_query)
        cursor.execute(create_table_teams_query)
        cursor.execute(create_table_exercise_query)
        cursor.execute(create_table_scores_trigger_1)
        cursor.execute(create_table_scores_trigger_2)


create_tables_and_triggers()
