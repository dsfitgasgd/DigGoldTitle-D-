"""Repair reversible UTF-8-as-MySQL-latin1 seed text; dry run by default.

Run inside the backend container. --apply requires --backup PATH.
The JSON backup records every original value before any updates are committed.
"""
import argparse
import json
import os
from pathlib import Path

import pymysql
import redis


def restore(value):
    if not isinstance(value, str):
        return value
    # MySQL latin1 uses Windows-1252 with undefined bytes mapped to controls.
    mapping = {}
    for number in range(256):
        raw = bytes([number])
        try:
            char = raw.decode("cp1252")
        except UnicodeDecodeError:
            char = chr(number)
        mapping[char] = number
    try:
        restored = bytes(mapping[c] for c in value).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return value
    if any("\u4e00" <= c <= "\u9fff" for c in restored):
        return restored
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup")
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires --backup")
    connection = pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "news_app"),
        charset="utf8mb4",
    )
    fields = {
        "news_category": ["name"],
        "news": ["title", "description", "content", "author"],
        "user": ["nickname", "bio"],
    }
    changes = []
    try:
        with connection.cursor() as cursor:
            for table, columns in fields.items():
                names = ",".join(f"`{column}`" for column in columns)
                cursor.execute(f"SELECT id,{names} FROM `{table}`")
                for row in cursor.fetchall():
                    for column, original in zip(columns, row[1:]):
                        repaired = restore(original)
                        if repaired != original:
                            changes.append(dict(table=table, id=row[0], column=column,
                                                original=original, repaired=repaired))
            print(f"Reversible corrupted fields: {len(changes)}")
            if not args.apply or not changes:
                return
            with Path(args.backup).open("x", encoding="utf-8") as backup:
                json.dump(changes, backup, ensure_ascii=True, indent=2)
                backup.flush()
                os.fsync(backup.fileno())
            for change in changes:
                cursor.execute(
                    f"UPDATE `{change['table']}` SET `{change['column']}`=%s "
                    f"WHERE id=%s AND BINARY `{change['column']}`=BINARY %s",
                    (change["repaired"], change["id"], change["original"]),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("Row changed concurrently; transaction rolled back")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    cache = redis.Redis(host=os.environ["REDIS_HOST"], db=int(os.getenv("REDIS_DB", "0")))
    cache.delete("news:categories")
    for key in cache.scan_iter(match="news_list:*"):
        cache.delete(key)
    cache.close()
    print("Repair committed; project news caches cleared.")


if __name__ == "__main__":
    main()
