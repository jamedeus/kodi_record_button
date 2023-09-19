import os
import xbmcvfs
import datetime
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine, Float, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from paths import output_path, database_path


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

    # Track if user has renamed the file (prevent auto delete)
    renamed: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"GeneratedFile(id={self.id!r}, output={self.output!r}, timestamp={self.timestamp!r})"


# Create engine with connection pooling disabled (causes Kodi to hang on exit)
engine = create_engine(f'sqlite:///{database_path}?timeout=5', poolclass=NullPool)
# NOTE: metadata is not created because it causes the script to hang when run
# within Kodi addon context (cause undetermined, possibly related to VFS)
# Instead a template database with tables pre-created is copied from /resources


# Returns current timestamp in YYYY-MM-DD_HH:MM:SS.MS syntax
def get_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')


def log_generated_file(source, start_time, duration, filename):
    with Session(engine) as session:
        new = GeneratedFile(
            source=source,
            output=f'{filename}.mp4',
            start_time=start_time,
            duration=duration,
            timestamp=get_timestamp(),
            renamed=False
        )

        session.add(new)
        session.commit()


# Returns payload for get_history endpoint
def load_history_json():
    # Query output filename and timestamp columns
    with Session(engine) as session:
        query = session.query(GeneratedFile.output, GeneratedFile.timestamp)
        history = {entry.timestamp: entry.output for entry in query}

    # Convert to dict with timestamp as key, filename as value
    return history


# Takes existing filename and new name, updates in database and renames on disk
def rename_entry(old, new):
    # If file exists on disk, rename
    if xbmcvfs.exists(os.path.join(output_path, old)):
        xbmcvfs.rename(os.path.join(output_path, old), os.path.join(output_path, new))

    # Rename in database
    with Session(engine) as session:
        entry = session.query(GeneratedFile).filter_by(output=old).first()
        entry.output = new
        entry.renamed = True
        session.commit()


# Takes output filename, deletes from database and disk
def delete_entry(filename):
    # Delete from database
    with Session(engine) as session:
        entry = session.query(GeneratedFile).filter_by(output=filename).first()
        session.delete(entry)
        session.commit()

    # If file exists on disk, delete
    if xbmcvfs.exists(os.path.join(output_path, filename)):
        xbmcvfs.delete(os.path.join(output_path, filename))


# Takes filename, returns True if already exists in database
def is_duplicate(filename):
    with Session(engine) as session:
        if session.query(GeneratedFile).filter_by(output=filename).first():
            return True
    return False
