import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.base import Base

# Import models so that Base.metadata is populated.
# Import models so that Base.metadata is populated.
from app.db.models.user import User  # noqa: F401
from app.db.models.conversation import Conversation  # noqa: F401
from app.db.models.message import Message  # noqa: F401
from app.db.models.extraction import Extraction  # noqa: F401
from app.db.models.semantic_memory import SemanticMemory  # noqa: F401
from app.db.models.semantic_relationship import SemanticRelationship  # noqa: F401
from app.db.models.subscription import Subscription  # noqa: F401
from app.db.models.usage import UsageTracking  # noqa: F401


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True if connection.dialect.name == "sqlite" else False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations():
    if context.is_offline_mode():
        context.configure(
            url=settings.database_url,
            target_metadata=target_metadata,
            literal_binds=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        asyncio.run(run_migrations_online())


run_migrations()

