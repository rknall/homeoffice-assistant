# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""User references of a restored database: re-pointing and orphan check.

A restore that keeps the current admin removes every user of the backup. The
rows referencing those users are re-pointed to the admin, dropped when the
admin already holds an equivalent row, and finally checked for leftovers. The
tables come from the database file itself, so plugin tables count too, loaded
or not.
"""

import logging
import uuid

from sqlalchemy import (
    Column,
    MetaData,
    String,
    bindparam,
    delete,
    exists,
    literal_column,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import BindParameter

from src.models import User, UserRole

logger = logging.getLogger(__name__)

ROLE_USER = UserRole.__table__.c.user_id

INDEXES = text(
    'SELECT name FROM pragma_index_list(:table) WHERE "unique" AND NOT partial'
)
INDEX_COLUMNS = text("SELECT name FROM pragma_index_info(:index) ORDER BY seqno")
FOREIGN_KEY_CHECK = text("PRAGMA foreign_key_check")


def _user_fk_columns(db: Session) -> list[Column]:
    """List every column of the database file that references ``users.id``.

    The tables are reflected from the file, not taken from the model metadata:
    plugin models are only imported for loaded plugins, and a restored file can
    hold tables the models do not describe. Only columns with a declared
    foreign key to ``users`` are found, so every plugin column holding a user
    id must be declared as ``ForeignKey("users.id")``; an undeclared one keeps
    the id of a removed user.

    Args:
        db: Session on the restored database.

    Returns:
        The reflected user columns, in table dependency order.
    """
    metadata = MetaData()
    metadata.reflect(bind=db.connection())
    users = metadata.tables[User.__tablename__]
    return [
        fk.parent
        for table in metadata.sorted_tables
        for fk in table.foreign_keys
        if fk.column is users.c.id
    ]


def _unique_keys(db: Session, column: Column) -> list[list[Column]]:
    """Return, per unique index holding the column, its other columns.

    SQLite keeps every PRIMARY KEY (except the rowid), UNIQUE constraint,
    inline or table-level, and unique index as a unique index, so the pragma
    sees what reflection misses. Partial and expression indexes are skipped.

    Args:
        db: Session on the restored database.
        column: A reflected user column.

    Returns:
        One list of the other key columns per unique index; an index on the
        column alone gives an empty list. Empty when the column is not part
        of any unique key.
    """
    table = column.table
    keys = []
    for index in db.execute(INDEXES, {"table": table.name}).scalars():
        names = db.execute(INDEX_COLUMNS, {"index": index}).scalars().all()
        if None in names or column.name not in names:
            continue
        keys.append([table.c[n] for n in names if n != column.name])
    return keys


def _take_over(
    db: Session, column: Column, keys: list[list[Column]], admin: BindParameter
) -> tuple[int, int]:
    """Hand the rows of other users in a unique user column to the admin.

    Rows are handled one at a time in ``rowid`` order. A row is deleted when
    the admin already owns a row with the same key (NULL equal to NULL) in any
    of the unique indexes, otherwise it is re-pointed. So the lowest ``rowid``
    wins among several users, and later rows see the ones already taken over.

    Args:
        db: Session on the restored database.
        column: A reflected user column that is part of a unique key.
        keys: Its unique keys from ``_unique_keys``, never empty.
        admin: The admin id as a bound parameter.

    Returns:
        Tuple of (rows re-pointed, rows deleted).
    """
    table = column.table
    row_id = literal_column("rowid")
    owned = table.alias("owned")
    conflict = or_(
        *(
            exists().where(
                owned.c[column.name] == admin,
                *(owned.c[k.name].is_not_distinct_from(k) for k in key),
            )
            for key in keys
        )
    )
    rowids = db.execute(
        select(row_id)
        .select_from(table)
        .where(column.is_not(None), column != admin)
        .order_by(row_id)
    ).scalars()
    moved = dropped = 0
    for rowid in rowids.all():
        if db.execute(delete(table).where(row_id == rowid, conflict)).rowcount:
            dropped += 1
            continue
        db.execute(update(table).where(row_id == rowid).values({column.name: admin}))
        moved += 1
    return moved, dropped


def reassign_user_rows(db: Session, admin_id: uuid.UUID) -> None:
    """Point every reference to a removed user at the admin, or drop the row.

    Every column of the file with a foreign key to ``users.id`` is handled:

    - Columns outside any unique key are re-pointed first, so a unique key
      containing such a column is compared as the admin will see it.
    - Role assignments (``user_roles.user_id``) of other users are deleted.
    - Every other column in a PRIMARY KEY, UNIQUE constraint or unique index
      is taken over row by row in ``rowid`` order: a row is deleted when the
      admin already owns one with the same key in any of these indexes (NULL
      counts as equal), otherwise it is re-pointed. The lowest ``rowid`` wins
      among several users.

    Unique keys are read from SQLite's index list. Partial and expression
    unique indexes are not taken over; a row clashing on one raises
    ``IntegrityError``, so the restore fails without changing anything. NULL
    stays NULL. Ids are bound as 32-char hex text, the stored format of both
    core ``CHAR(32)`` and plugin ``NUMERIC`` columns.

    Args:
        db: Session on the restored database.
        admin_id: The preserved admin.
    """
    admin = bindparam("admin_id", admin_id.hex, type_=String)
    roles, unique, plain = [], [], []
    for column in _user_fk_columns(db):
        if column.table.name == ROLE_USER.table.name and column.name == ROLE_USER.name:
            roles.append(column)
        elif keys := _unique_keys(db, column):
            unique.append((column, keys))
        else:
            plain.append(column)

    for column in plain:
        stmt = (
            update(column.table)
            .where(column.is_not(None), column != admin)
            .values({column.name: admin})
        )
        count = db.execute(stmt).rowcount
        logger.info(f"{column.table.name}.{column.name}: {count} rows re-pointed")
    for column in roles:
        count = db.execute(delete(column.table).where(column != admin)).rowcount
        logger.info(f"{column.table.name}.{column.name}: {count} rows deleted")
    for column, keys in unique:
        moved, dropped = _take_over(db, column, keys, admin)
        logger.info(
            f"{column.table.name}.{column.name}: {moved} rows re-pointed, "
            f"{dropped} rows deleted"
        )


def find_user_orphans(db: Session) -> dict[str, int]:
    """Count the rows per table that still reference a missing user.

    Uses ``PRAGMA foreign_key_check``, so every declared foreign key to
    ``users`` in the file is checked, whichever models are loaded.

    Args:
        db: Session on the database to check.

    Returns:
        Row count per child table; empty when no row references a missing
        user.
    """
    orphans: dict[str, int] = {}
    for row in db.execute(FOREIGN_KEY_CHECK):
        if row[2] == User.__tablename__:
            orphans[row[0]] = orphans.get(row[0], 0) + 1
    return orphans
