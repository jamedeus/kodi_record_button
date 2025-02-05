'''SqlAlchemy ORM model used to track generated clips, utility functions used
to find, modify, and delete existing entries.
'''

# pylint: disable=too-few-public-methods

import os
import logging
import datetime
import xbmc
import xbmcvfs
import xbmcaddon
from sqlalchemy import URL
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy import create_engine, Float, String, Boolean, select, desc, or_
from kodi_gui import autodelete_notification
from paths import output_path, database_path


def get_mysql_url():
    '''Reads MySQL address and credentials from Kodi settings, returns URL object.'''
    addon = xbmcaddon.Addon()
    return URL.create(
        'mysql+pymysql',
        username=addon.getSetting('mysql_user'),
        password=addon.getSetting('mysql_pass'),
        host=addon.getSetting('mysql_host'),
        port=addon.getSetting('mysql_port'),
        database=addon.getSetting('mysql_db')
    )


def get_configured_engine():
    '''Returns SQLAlchemy Engine for currently-configured database (Kodi
    settings). All databases echo to Kodi logs, see SQLAlchemyLogHandler.
    '''
    db_type = xbmcaddon.Addon().getSetting('db_type')
    if db_type == "SQLite":
        # Workaround: return existing sqlite engine (creating new enginge makes
        # Kodi hang on exit, leaving open doesn't seem to have downsides)
        return local_engine
    if db_type == "MySQL":
        # Create new engine for remote MySQL server
        xbmc.log("Database: Creating MySQL engine", xbmc.LOGINFO)
        return create_engine(get_mysql_url(), poolclass=NullPool, echo=True)
    raise ValueError("Unsupported value for 'db_type' setting")


def replace_engine():
    '''Called when user changes settings, replaces the global engine object
    used by all functions with appropriate engine for current settings.
    '''
    global engine  # pylint: disable=global-statement
    # Get new engine based on current settings
    engine = get_configured_engine()
    # Create database tables if they don't exist
    Base.metadata.create_all(engine)


class SQLAlchemyLogHandler(logging.Handler):
    '''Redirects SQLAlchemy echo to Kodi log.'''
    def emit(self, record):
        xbmc.log(self.format(record), level=xbmc.LOGDEBUG)


# Somehow this fixes the hang on exit issue when NullPool is not used
logging.basicConfig(handlers=[SQLAlchemyLogHandler()])


class Base(DeclarativeBase):  # pylint: disable=missing-class-docstring
    pass


class GeneratedFile(Base):
    '''Stores all parameters used to generate a single file.'''
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Absolute path to source file
    source: Mapped[str] = mapped_column(String(999), nullable=False)

    # Output filename, no path, max 50 characters
    output: Mapped[str] = mapped_column(String(50), nullable=False)

    # Start timestamp (playtime seconds), duration (seconds)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)

    # Request timestamp in YYYY-MM-DD_HH:MM:SS.MS syntax
    timestamp: Mapped[str] = mapped_column(String(26), nullable=False)

    # Show and episode names, used in history search
    show_name: Mapped[str] = mapped_column(String(100), nullable=False)
    episode_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Track if user has renamed the file (prevent auto delete)
    renamed: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"GeneratedFile(id={self.id!r}, output={self.output!r}, timestamp={self.timestamp!r})"  # pylint: disable=line-too-long


# Create engine for local sqlite database
# This persists even if database type is changed in settings because closing and
# re-opening causes Kodi to hang on exit
local_engine = create_engine(f'sqlite:///{database_path}?timeout=5', echo=True)

# Create engine for database configured in Kodi settings, used by functions below
# Will return local_engine if SQLite is configured, otherwise returns new engine
# for configured external database (MySQL or PostgreSQL)
engine = get_configured_engine()

# Create database tables if they don't exist
Base.metadata.create_all(engine)


def get_timestamp():
    '''Returns current timestamp in YYYY-MM-DD_HH:MM:SS.MS syntax.'''
    return datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')


def get_filename_query(filename):
    '''Takes filename, returns SELECT statement for entries with identical filename.'''
    return select(GeneratedFile).where(GeneratedFile.output == filename)


def get_orm_entry(filename):
    '''Takes existing clip filename, returns ORM entry.'''
    with Session(engine) as session:
        return session.scalar(get_filename_query(filename))


def log_generated_file(source, start_time, duration, filename, show_name, episode_name):  # pylint: disable=too-many-arguments
    '''Takes parameters used to generate clip, logs ORM entry to database.'''
    with Session(engine) as session:
        session.add(GeneratedFile(
            source=source,
            output=f'{filename}.mp4',
            start_time=start_time,
            duration=duration,
            timestamp=get_timestamp(),
            show_name=show_name,
            episode_name=episode_name,
            renamed=False
        ))
        session.commit()


def load_history_json():
    '''Returns list of (timestamp, filename) tuples for every file in database.'''

    # Query output filename and timestamp columns
    with Session(engine) as session:
        stmt = select(
            GeneratedFile.timestamp,
            GeneratedFile.output
        ).order_by(
            desc(GeneratedFile.timestamp)
        )
        result = session.execute(stmt).all()
        # Convert to list of tuples with timestamp and filename
        history = [tuple(entry) for entry in result]

    return history


def load_history_search_results(search_string):
    '''Takes search_string, returns list of (timestamp, filename) tuples for
    entries with filename, show_name, or episode_name containing search_string.
    '''

    # Query output filename and timestamp columns
    with Session(engine) as session:
        stmt = select(
            GeneratedFile.timestamp,
            GeneratedFile.output
        ).where(
            or_(
                GeneratedFile.output.contains(search_string),
                GeneratedFile.show_name.contains(search_string),
                GeneratedFile.episode_name.contains(search_string)
            )
        ).order_by(
            desc(GeneratedFile.timestamp)
        )
        result = session.execute(stmt).all()
        # Convert to list of tuples with timestamp and filename
        history = [tuple(entry) for entry in result]

    return history


def rename_entry(old, new):
    '''Takes existing clip filename and new name, updates in database and
    renames file on disk.
    '''

    # If file exists on disk, rename
    if xbmcvfs.exists(os.path.join(output_path, old)):
        xbmcvfs.rename(
            os.path.join(output_path, old),
            os.path.join(output_path, new)
        )

    # Rename in database
    with Session(engine) as session:
        entry = session.scalar(get_filename_query(old))
        entry.output = new
        entry.renamed = True
        session.commit()


def delete_entry(filename):
    '''Takes clip filename, deletes from database and disk.'''

    # Delete from database
    with Session(engine) as session:
        entry = session.scalar(get_filename_query(filename))
        session.delete(entry)
        session.commit()

    # If file exists on disk, delete
    if xbmcvfs.exists(os.path.join(output_path, filename)):
        xbmcvfs.delete(os.path.join(output_path, filename))


def is_duplicate(filename):
    '''Takes clip filename, returns True if it already exists in database.'''
    with Session(engine) as session:
        if session.scalar(get_filename_query(filename)):
            return True
    return False


def get_older_than(days):
    '''Takes days (int), returns all ORM objects older than days.'''

    # Get datetime object of cutoff date, convert to string
    cutoff = datetime.datetime.today() - datetime.timedelta(days=days)
    cutoff = cutoff.strftime('%Y-%m-%d_%H:%M:%S.%f')

    # Get ORM representations of all entries older than cutoff
    with Session(engine) as session:
        stmt = select(
            GeneratedFile
        ).where(
            # String comparison required, cannot parse database
            # timestamp to datetime object within where clause
            GeneratedFile.timestamp <= cutoff
        )
        results = session.scalars(stmt).all()

    return results


def bulk_delete(entries, keep_renamed=False):
    '''Takes list of ORM objects, deletes all from database and disk.
    Optional bool arg prevents user-renamed files from being deleted.
    '''

    # Track number of deleted files
    deleted = 0

    with Session(engine) as session:
        for entry in entries:
            # Skip renamed files if setting enabled
            if keep_renamed and entry.renamed:
                continue

            xbmc.log(f"Automatically deleting {entry.output}", xbmc.LOGINFO)

            # If file exists on disk, delete
            if xbmcvfs.exists(os.path.join(output_path, entry.output)):
                xbmcvfs.delete(os.path.join(output_path, entry.output))

            # Delete from database
            session.delete(entry)
            deleted += 1

        session.commit()

    # Show notification if clips were deleted
    if deleted > 0:
        autodelete_notification(deleted)
    xbmc.log(f"Autodelete complete, deleted {deleted} clips", xbmc.LOGINFO)


def autodelete():
    '''Finds clips older than "delete_after_days" setting, deletes from disk
    and database. Called during server startup if autodelete option is enabled.
    Skips user-renamed files if "keep_renamed_files" setting is True.
    '''

    # Read user settings (number of days, whether to keep renamed files)
    days = int(xbmcaddon.Addon().getSetting('delete_after_days'))

    if xbmcaddon.Addon().getSetting('keep_renamed_files') == 'true':
        xbmc.log(f"Deleting clips older than {days} days (keeping renamed)", xbmc.LOGINFO)
        bulk_delete(get_older_than(days), True)

    else:
        xbmc.log(f"Deleting clips older than {days} days", xbmc.LOGINFO)
        bulk_delete(get_older_than(days), False)
