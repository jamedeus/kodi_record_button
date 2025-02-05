# pylint: disable=line-too-long, missing-module-docstring, missing-function-docstring

import os
import datetime
import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
import mock_kodi_modules
from paths import database_path
from database import (
    get_mysql_url,
    get_configured_engine,
    Base,
    GeneratedFile,
    engine,
    get_timestamp,
    get_filename_query,
    get_orm_entry,
    log_generated_file,
    load_history_json,
    load_history_search_results,
    rename_entry,
    delete_entry,
    is_duplicate,
    autodelete
)


class TestDatabaseBackends(unittest.TestCase):
    def test_get_mysql_url(self):
        # Create mock getSettings that returns MySQL credentials
        def mock_get_settings(setting):
            if setting == 'mysql_user':
                return 'admin'
            if setting == 'mysql_pass':
                return 'hunter2'
            if setting == 'mysql_host':
                return '127.0.0.1'
            if setting == 'mysql_port':
                return '8921'
            if setting == 'mysql_db':
                return 'mydb'
            return None

        # Call get_mysql_url with mocked getSettings
        with patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:
            mock_addon.return_value.getSetting = mock_get_settings
            url = get_mysql_url()
            # Confirm correct dialect and driver
            self.assertEqual(url.get_backend_name(), 'mysql')
            self.assertEqual(url.get_driver_name(), 'pymysql')
            # Confirm correct user and address params
            self.assertEqual(url.username, 'admin')
            self.assertEqual(url.password, 'hunter2')
            self.assertEqual(url.host, '127.0.0.1')
            self.assertEqual(url.port, 8921)
            self.assertEqual(url.database, 'mydb')

    def test_create_engine(self):
        # Call with no mock, should return local sqlite database
        new_engine = get_configured_engine()
        self.assertEqual(new_engine.name, 'sqlite')
        self.assertEqual(new_engine.driver, 'pysqlite')
        self.assertEqual(str(new_engine.url), 'sqlite:///./history.db?timeout=5')
        self.assertEqual(new_engine.url.database, database_path)

    def test_create_engine_mysql(self):
        # Mock getSettings to return MySQL
        # Mock other methods to confirm called
        with patch('database.create_engine', MagicMock()) as mock_create_engine, \
             patch('database.get_mysql_url', MagicMock()) as mock_get_mysql_url, \
             patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:

            mock_addon.return_value.getSetting.return_value = 'MySQL'
            # Get engine, confirm correct methods called
            get_configured_engine()
            self.assertTrue(mock_create_engine.called)
            self.assertTrue(mock_get_mysql_url.called)


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import engine from database.py
        cls.engine = engine
        # Create test database and tables in working directory
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        # Delete test database
        os.remove('history.db')

    def tearDown(self):
        # Delete all database entries after each test
        with Session(self.engine) as session:
            session.query(GeneratedFile).delete()
            session.commit()

    def test_generated_file_orm(self):
        # Create test entry, confirm repr method prints correct string
        entry = GeneratedFile(id=1, output='test.mp4', timestamp='2023-09-23_23:19:39.681760')
        self.assertEqual(
            repr(entry),
            "GeneratedFile(id=1, output='test.mp4', timestamp='2023-09-23_23:19:39.681760')"
        )

    def test_get_timestamp(self):
        # Confirm method returns timestamp string which can be parsed back into datetime object
        timestamp = get_timestamp()
        self.assertIsInstance(timestamp, str)
        self.assertIsInstance(datetime.datetime.fromisoformat(timestamp), datetime.datetime)

    def test_get_filename_query(self):
        # Confirm method returns SELECT statement
        query = get_filename_query('test.mp4')
        self.assertEqual(
            str(query),
            'SELECT history.id, history.source, history.output, history.start_time, history.duration, history.timestamp, history.show_name, history.episode_name, history.renamed \nFROM history \nWHERE history.output = :output_1'
        )

    def test_get_orm_entry(self):
        # Create test entry
        with Session(self.engine) as session:
            session.add(GeneratedFile(
                id=1,
                source='/path/to/source.mp4',
                output='test.mp4',
                start_time=23.4567,
                duration=100.0,
                timestamp='2023-09-23_23:19:39.681760',
                show_name='Show Name',
                episode_name='Episode Name',
                renamed=False
            ))
            session.commit()

        # Query test entry, confirm attributes
        entry = get_orm_entry('test.mp4')
        self.assertEqual(entry.id, 1)
        self.assertEqual(entry.output, 'test.mp4')
        self.assertEqual(entry.timestamp, '2023-09-23_23:19:39.681760')

    def test_log_generated_file(self):
        # Create test entry
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='logged',
            show_name='Show Name',
            episode_name='Episode Name'
        )

        # Confirm entry created
        entry = get_orm_entry('logged.mp4')
        self.assertEqual(entry.output, 'logged.mp4')
        self.assertEqual(entry.show_name, 'Show Name')

    def test_load_history_json(self):
        # Create test entry
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='test',
            show_name='Show Name',
            episode_name='Episode Name'
        )

        # Confirm method returns list containing a single tuple with 2 params
        history = load_history_json()
        self.assertEqual(len(history), 1)
        self.assertIsInstance(history, list)
        self.assertIsInstance(history[0], tuple)
        self.assertEqual(len(history[0]), 2)
        self.assertEqual(history[0][1], 'test.mp4')

    def test_load_history_search_results(self):
        # Create test entries with different filenames and show names
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='search for this',
            show_name='First Show',
            episode_name='Episode Title'
        )
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='E7JI8wNLeCr7xopi',
            show_name='First Show',
            episode_name='Episode Title'
        )
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='IylJp5LtP5A7D9Lb',
            show_name='Second Show',
            episode_name='Episode Title'
        )

        # Search for a substring from the first filename, confirm 1 result
        search_results = load_history_search_results("for this")
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0][1], 'search for this.mp4')

        # Search for a show name shared by 2 entries, confirm 2 results
        search_results = load_history_search_results("First Show")
        self.assertEqual(len(search_results), 2)
        self.assertEqual(search_results[0][1], 'E7JI8wNLeCr7xopi.mp4')
        self.assertEqual(search_results[1][1], 'search for this.mp4')

        # Search for episode name shared by all 3, confirm 3 results
        search_results = load_history_search_results("Episode Title")
        self.assertEqual(len(search_results), 3)
        self.assertEqual(search_results[0][1], 'IylJp5LtP5A7D9Lb.mp4')
        self.assertEqual(search_results[1][1], 'E7JI8wNLeCr7xopi.mp4')
        self.assertEqual(search_results[2][1], 'search for this.mp4')

    def test_rename_entry(self):
        # Create test file to rename
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='original',
            show_name='Show Name',
            episode_name='Episode Name'
        )

        # Rename, confirm old name no longer exists, new name does exist
        rename_entry('original.mp4', 'new_name.mp4')
        self.assertIsNone(get_orm_entry('original.mp4'))
        entry = get_orm_entry('new_name.mp4')
        self.assertEqual(entry.output, 'new_name.mp4')

    def test_delete_entry(self):
        # Create test file to delete, confirm exists
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='delete me',
            show_name='Show Name',
            episode_name='Episode Name'
        )
        self.assertIsNotNone(get_orm_entry('delete me.mp4'))

        # Delete, confirm no longer exists
        delete_entry('delete me.mp4')
        self.assertIsNone(get_orm_entry('delete me.mp4'))

    def test_is_duplicate(self):
        # Create test file
        log_generated_file(
            source='/path/to/source.mp4',
            start_time=23.4567,
            duration=100.0,
            filename='exists',
            show_name='Show Name',
            episode_name='Episode Name'
        )

        # Function should return True for existing filename, False for new
        self.assertTrue(is_duplicate('exists.mp4'))
        self.assertFalse(is_duplicate('new.mp4'))

    def test_autodelete(self):
        # Get current datetime object
        now = datetime.datetime.now()

        # Create 10 test entries each 1 day apart
        with Session(self.engine) as session:
            for i in range(0, 10):
                dt = now - datetime.timedelta(days=i)

                session.add(GeneratedFile(
                    source='/path/to/source.mp4',
                    output=f'autodelete{i}.mp4',
                    start_time=23.4567,
                    duration=100.0,
                    timestamp=dt.strftime('%Y-%m-%d_%H:%M:%S.%f'),
                    show_name='Show Name',
                    episode_name='Episode Name',
                    renamed=False
                ))
                session.commit()

        # Confirm all 10 exist
        self.assertEqual(len(load_history_json()), 10)

        # Create mock getSettings to simulate autodelete enabled, delete after 5 days, don't keep renamed
        def mock_get_settings(setting):
            if setting == 'delete_after_days':
                return '5'
            if setting == 'keep_renamed_files':
                return 'false'
            return None

        # Call autodelete with mocked method
        with patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:
            mock_addon.return_value.getSetting = mock_get_settings
            autodelete()

        # Confirm only 5 most-recent entries left
        history = load_history_json()
        self.assertEqual(len(history), 5)
        self.assertEqual(history[0][1], 'autodelete0.mp4')
        self.assertEqual(history[1][1], 'autodelete1.mp4')
        self.assertEqual(history[2][1], 'autodelete2.mp4')
        self.assertEqual(history[3][1], 'autodelete3.mp4')
        self.assertEqual(history[4][1], 'autodelete4.mp4')

    def test_autodelete_keep_renamed(self):
        # Get current datetime object
        now = datetime.datetime.now()

        # Create 10 test entries each 1 day apart
        # Mark every odd-numbered iteration as renamed
        with Session(self.engine) as session:
            for i in range(0, 10):
                dt = now - datetime.timedelta(days=i)

                session.add(GeneratedFile(
                    source='/path/to/source.mp4',
                    output=f'autodelete{i}.mp4',
                    start_time=23.4567,
                    duration=100.0,
                    timestamp=dt.strftime('%Y-%m-%d_%H:%M:%S.%f'),
                    show_name='Show Name',
                    episode_name='Episode Name',
                    renamed=bool(i % 2)
                ))
                session.commit()

        # Confirm all 10 exist
        self.assertEqual(len(load_history_json()), 10)

        # Create mock getSettings to simulate autodelete enabled, delete after 5 days, keep renamed
        def mock_get_settings(setting):
            if setting == 'delete_after_days':
                return '5'
            if setting == 'keep_renamed_files':
                return 'true'
            return None

        # Call autodelete with mocked method
        with patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:
            mock_addon.return_value.getSetting = mock_get_settings
            autodelete()

        # Confirm only 8 entries left (5 most recent + 3 renamed)
        history = load_history_json()
        self.assertEqual(len(history), 8)
        self.assertEqual(history[0][1], 'autodelete0.mp4')
        self.assertEqual(history[1][1], 'autodelete1.mp4')
        self.assertEqual(history[2][1], 'autodelete2.mp4')
        self.assertEqual(history[3][1], 'autodelete3.mp4')
        self.assertEqual(history[4][1], 'autodelete4.mp4')
        self.assertEqual(history[5][1], 'autodelete5.mp4')
        self.assertEqual(history[6][1], 'autodelete7.mp4')
        self.assertEqual(history[7][1], 'autodelete9.mp4')
