"""
Search indexer: syncs card prints from MySQL to Meilisearch.
Print-first search with cross-language support via keywords_localized.
"""
import logging
from typing import Any

import pymysql
from meilisearch import Client
from meilisearch.errors import MeilisearchError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Batch size for Meilisearch add_documents
BATCH_SIZE = 5000


def _get_mysql_connection():
    """Create a MySQL connection from settings."""
    settings = get_settings()
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _get_meilisearch_client() -> Client:
    """Create Meilisearch client from settings."""
    settings = get_settings()
    return Client(
        settings.MEILISEARCH_URL,
        api_key=settings.MEILISEARCH_MASTER_KEY,
    )


def _build_mtg_translation_map(conn: pymysql.Connection) -> dict[str, list[str]]:
    """
    Build oracle_id -> list of all printed_name variations (for cross-language search).
    Uses cards.name; if cards_prints has printed_name we also collect those for full i18n.
    """
    map_oracle_to_names: dict[str, list[str]] = {}
    with conn.cursor() as cur:
        # 1) Canonical name per oracle_id from cards
        cur.execute(
            """
            SELECT oracle_id, name
            FROM cards
            WHERE oracle_id IS NOT NULL AND name IS NOT NULL AND name != ''
            """
        )
        for row in cur.fetchall():
            oid = row["oracle_id"]
            name = (row["name"] or "").strip()
            if not name:
                continue
            if oid not in map_oracle_to_names:
                map_oracle_to_names[oid] = []
            if name not in map_oracle_to_names[oid]:
                map_oracle_to_names[oid].append(name)
        # 2) If cards_prints has printed_name, add all per-print names (e.g. Italian "Mare Sotterraneo")
        try:
            cur.execute(
                """
                SELECT oracle_id, printed_name AS name
                FROM cards_prints
                WHERE oracle_id IS NOT NULL AND printed_name IS NOT NULL AND printed_name != ''
                """
            )
            for row in cur.fetchall():
                oid = row["oracle_id"]
                name = (row["name"] or "").strip()
                if not name:
                    continue
                if oid not in map_oracle_to_names:
                    map_oracle_to_names[oid] = []
                if name not in map_oracle_to_names[oid]:
                    map_oracle_to_names[oid].append(name)
        except pymysql.err.ProgrammingError:
            # Column printed_name may not exist yet
            pass
    return map_oracle_to_names


def _index_mtg_prints(
    conn: pymysql.Connection,
    client: Client,
    index_name: str,
    translation_map: dict[str, list[str]],
    batch_size: int,
) -> int:
    """Index MTG prints from cards_prints JOIN sets, cards, games."""
    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                cp.id AS print_id,
                cp.oracle_id,
                COALESCE(c.name, '') AS printed_name,
                cp.image_path,
                COALESCE(s.name, '') AS set_name,
                COALESCE(g.slug, 'mtg') AS game_slug
            FROM cards_prints cp
            INNER JOIN cards c ON c.oracle_id = cp.oracle_id
            INNER JOIN sets s ON s.id = cp.set_id
            INNER JOIN games g ON g.id = s.game_id
            WHERE cp.oracle_id IS NOT NULL
            ORDER BY cp.id
            """
        )
        batch: list[dict[str, Any]] = []
        for row in cur:
            print_id = row["print_id"]
            oracle_id = row["oracle_id"] or ""
            printed_name = (row["printed_name"] or "").strip() or "Unknown"
            image_path = (row["image_path"] or "").strip()
            set_name = (row["set_name"] or "").strip()
            game_slug = (row["game_slug"] or "mtg").strip()

            keywords_localized = list(
                translation_map.get(oracle_id, [printed_name])
            )
            if printed_name not in keywords_localized:
                keywords_localized.insert(0, printed_name)

            doc = {
                "id": f"mtg_{print_id}",
                "name": printed_name,
                "set_name": set_name,
                "game_slug": game_slug,
                "image": image_path,
                "keywords_localized": keywords_localized,
            }
            batch.append(doc)
            if len(batch) >= batch_size:
                client.index(index_name).add_documents(batch)
                count += len(batch)
                logger.info("Indexed MTG batch: %d docs (total so far: %d)", len(batch), count)
                batch = []

        if batch:
            client.index(index_name).add_documents(batch)
            count += len(batch)
            logger.info("Indexed final MTG batch: %d docs (total: %d)", len(batch), count)
    return count


def _build_op_translation_map(conn: pymysql.Connection) -> dict[str, list[str]]:
    """Build card_id -> list of names for One Piece (name_en; add name_it etc. if present)."""
    map_card_to_names: dict[str, list[str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT card_id, name_en
            FROM op_cards
            WHERE card_id IS NOT NULL
            """
        )
        for row in cur.fetchall():
            cid = row["card_id"]
            name = (row["name_en"] or "").strip()
            if not name:
                continue
            if cid not in map_card_to_names:
                map_card_to_names[cid] = []
            if name not in map_card_to_names[cid]:
                map_card_to_names[cid].append(name)
    return map_card_to_names


def _index_op_prints(
    conn: pymysql.Connection,
    client: Client,
    index_name: str,
    translation_map: dict[str, list[str]],
    batch_size: int,
) -> int:
    """Index One Piece prints from op_prints JOIN op_cards, sets, games."""
    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                op.id AS print_id,
                op.card_id,
                COALESCE(oc.name_en, '') AS printed_name,
                op.image_path,
                COALESCE(s.name, '') AS set_name,
                COALESCE(g.slug, 'op') AS game_slug
            FROM op_prints op
            INNER JOIN op_cards oc ON oc.card_id = op.card_id
            INNER JOIN sets s ON s.id = op.set_id
            INNER JOIN games g ON g.id = s.game_id
            ORDER BY op.id
            """
        )
        batch: list[dict[str, Any]] = []
        for row in cur:
            print_id = row["print_id"]
            card_id = row["card_id"] or ""
            printed_name = (row["printed_name"] or "").strip() or "Unknown"
            image_path = (row["image_path"] or "").strip()
            set_name = (row["set_name"] or "").strip()
            game_slug = (row["game_slug"] or "op").strip()

            keywords_localized = list(
                translation_map.get(card_id, [printed_name])
            )
            if printed_name not in keywords_localized:
                keywords_localized.insert(0, printed_name)

            doc = {
                "id": f"op_{print_id}",
                "name": printed_name,
                "set_name": set_name,
                "game_slug": game_slug,
                "image": image_path,
                "keywords_localized": keywords_localized,
            }
            batch.append(doc)
            if len(batch) >= batch_size:
                client.index(index_name).add_documents(batch)
                count += len(batch)
                logger.info("Indexed OP batch: %d docs (total so far: %d)", len(batch), count)
                batch = []

        if batch:
            client.index(index_name).add_documents(batch)
            count += len(batch)
            logger.info("Indexed final OP batch: %d docs (total: %d)", len(batch), count)
    return count


def _build_pk_translation_map(conn: pymysql.Connection) -> dict[str, list[str]]:
    """Build card_id -> list of names for Pokémon (name_en)."""
    map_card_to_names: dict[str, list[str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT card_id, name_en
            FROM pk_cards
            WHERE card_id IS NOT NULL
            """
        )
        for row in cur.fetchall():
            cid = row["card_id"]
            name = (row["name_en"] or "").strip()
            if not name:
                continue
            if cid not in map_card_to_names:
                map_card_to_names[cid] = []
            if name not in map_card_to_names[cid]:
                map_card_to_names[cid].append(name)
    return map_card_to_names


def _index_pk_prints(
    conn: pymysql.Connection,
    client: Client,
    index_name: str,
    translation_map: dict[str, list[str]],
    batch_size: int,
) -> int:
    """Index Pokémon prints from pk_prints JOIN pk_cards, sets, games. Uses image_url."""
    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                pp.id AS print_id,
                pp.card_id,
                COALESCE(pc.name_en, '') AS printed_name,
                pp.image_url AS image_path,
                COALESCE(s.name, '') AS set_name,
                COALESCE(g.slug, 'pk') AS game_slug
            FROM pk_prints pp
            INNER JOIN pk_cards pc ON pc.card_id = pp.card_id
            INNER JOIN sets s ON s.id = pp.set_id
            INNER JOIN games g ON g.id = s.game_id
            ORDER BY pp.id
            """
        )
        batch: list[dict[str, Any]] = []
        for row in cur:
            print_id = row["print_id"]
            card_id = row["card_id"] or ""
            printed_name = (row["printed_name"] or "").strip() or "Unknown"
            image_path = (row["image_path"] or "").strip()  # image_url mapped to image_path
            set_name = (row["set_name"] or "").strip()
            game_slug = (row["game_slug"] or "pk").strip()

            keywords_localized = list(
                translation_map.get(card_id, [printed_name])
            )
            if printed_name not in keywords_localized:
                keywords_localized.insert(0, printed_name)

            doc = {
                "id": f"pk_{print_id}",
                "name": printed_name,
                "set_name": set_name,
                "game_slug": game_slug,
                "image": image_path,
                "keywords_localized": keywords_localized,
            }
            batch.append(doc)
            if len(batch) >= batch_size:
                client.index(index_name).add_documents(batch)
                count += len(batch)
                logger.info("Indexed PK batch: %d docs (total so far: %d)", len(batch), count)
                batch = []

        if batch:
            client.index(index_name).add_documents(batch)
            count += len(batch)
            logger.info("Indexed final PK batch: %d docs (total: %d)", len(batch), count)
    return count


def _configure_meilisearch_index(client: Client, index_name: str) -> None:
    """Set searchable attributes: name, keywords_localized, set_name."""
    index = client.index(index_name)
    index.update_searchable_attributes(
        ["name", "keywords_localized", "set_name"]
    )


def run_indexer() -> dict[str, Any]:
    """
    Full reindex: build translation maps, index MTG then OP then PK, configure settings.
    Returns a summary with counts and any error message.
    """
    settings = get_settings()
    index_name = settings.MEILISEARCH_INDEX_NAME
    batch_size = settings.INDEXER_BATCH_SIZE or BATCH_SIZE
    result: dict[str, Any] = {
        "mtg": 0,
        "op": 0,
        "pk": 0,
        "total": 0,
        "error": None,
    }

    try:
        conn = _get_mysql_connection()
        client = _get_meilisearch_client()
    except Exception as e:
        logger.exception("Failed to connect to MySQL or Meilisearch")
        result["error"] = str(e)
        return result

    try:
        # Ensure index exists (create or replace)
        try:
            client.get_index(index_name)
        except MeilisearchError:
            client.create_index(index_name, {"primaryKey": "id"})

        # Translation maps (efficient single queries)
        logger.info("Building MTG translation map...")
        mtg_map = _build_mtg_translation_map(conn)
        logger.info("Building OP translation map...")
        op_map = _build_op_translation_map(conn)
        logger.info("Building PK translation map...")
        pk_map = _build_pk_translation_map(conn)

        # Index all games
        result["mtg"] = _index_mtg_prints(conn, client, index_name, mtg_map, batch_size)
        result["op"] = _index_op_prints(conn, client, index_name, op_map, batch_size)
        result["pk"] = _index_pk_prints(conn, client, index_name, pk_map, batch_size)
        result["total"] = result["mtg"] + result["op"] + result["pk"]

        _configure_meilisearch_index(client, index_name)
        logger.info("Reindex complete: mtg=%d op=%d pk=%d total=%d", result["mtg"], result["op"], result["pk"], result["total"])
    except Exception as e:
        logger.exception("Indexer failed")
        result["error"] = str(e)
    finally:
        conn.close()

    return result
