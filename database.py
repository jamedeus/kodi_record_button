import os
import xbmc
import xbmcvfs
import logging
import datetime
import xbmcaddon
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy import create_engine, Float, String, Boolean, select, desc, or_
from paths import output_path, database_path


# Redirect SQLAlchemy echo to Kodi log
class SQLAlchemyLogHandler(logging.Handler):
    def emit(self, record):
        xbmc.log(self.format(record), level=xbmc.LOGDEBUG)


# Somehow this fixes the hang on exit issue when NullPool is not used
logging.basicConfig(handlers=[SQLAlchemyLogHandler()])


class Base(DeclarativeBase):
    pass


# Store all parameters used to generate a single file
class GeneratedFile(Base):
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
        return f"GeneratedFile(id={self.id!r}, output={self.output!r}, timestamp={self.timestamp!r})"


# Create engine with logging enabled (merged into Kodi log by handler above)
engine = create_engine(f'sqlite:///{database_path}?timeout=5', echo=True)
# Create database tables if they don't exist
Base.metadata.create_all(engine)


# Returns current timestamp in YYYY-MM-DD_HH:MM:SS.MS syntax
def get_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')


# Takes filename, returns SELECT statement for entries with identical filename
def get_filename_query(filename):
    return select(GeneratedFile).where(GeneratedFile.output == filename)


# Takes filename, returns ORM entry
def get_orm_entry(filename):
    with Session(engine) as session:
        return session.scalar(get_filename_query(filename))


def log_generated_file(source, start_time, duration, filename, show_name, episode_name):
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


# Returns list of (timestamp, filename) tuples for every file in database
def load_history_json():
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


# Takes search_string, returns list of (timestamp, filename) tuples for each
# entry whose output filename, show_name, or episode_name contain search_string
def load_history_search_results(search_string):
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


# Takes existing filename and new name, updates in database and renames on disk
def rename_entry(old, new):
    # If file exists on disk, rename
    if xbmcvfs.exists(os.path.join(output_path, old)):
        xbmcvfs.rename(os.path.join(output_path, old), os.path.join(output_path, new))

    # Rename in database
    with Session(engine) as session:
        entry = session.scalar(get_filename_query(old))
        entry.output = new
        entry.renamed = True
        session.commit()


# Takes output filename, deletes from database and disk
def delete_entry(filename):
    # Delete from database
    with Session(engine) as session:
        entry = session.scalar(get_filename_query(filename))
        session.delete(entry)
        session.commit()

    # If file exists on disk, delete
    if xbmcvfs.exists(os.path.join(output_path, filename)):
        xbmcvfs.delete(os.path.join(output_path, filename))


# Takes filename, returns True if already exists in database
def is_duplicate(filename):
    with Session(engine) as session:
        if session.scalar(get_filename_query(filename)):
            return True
    return False


# Takes days (int), returns all ORM objects older than days
def get_older_than(days):
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


# Takes list of ORM objects, deletes all from db
# Optional bool arg prevents user-renamed files from being deleted
def bulk_delete(entries, keep_renamed=False):
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

        session.commit()
    xbmc.log(f"Autodelete complete, deleted {len(entries)} clips", xbmc.LOGINFO)


# Called during server startup if autodelete option is enabled
def autodelete():
    # Read user settings (number of days, whether to keep renamed files)
    days = int(xbmcaddon.Addon().getSetting('delete_after_days'))

    if xbmcaddon.Addon().getSetting('keep_renamed_files') == 'true':
        xbmc.log(f"Deleting clips older than {days} days (keeping renamed)", xbmc.LOGINFO)
        bulk_delete(get_older_than(days), True)

    else:
        xbmc.log(f"Deleting clips older than {days} days", xbmc.LOGINFO)
        bulk_delete(get_older_than(days), False)
