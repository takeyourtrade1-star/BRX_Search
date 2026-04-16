"""
Search indexer: syncs card prints from MySQL to Meilisearch.
Print-first search with centralized multilingual support via card_translations + keywords_localized.
"""
import logging
from datetime import date, datetime
from typing import Any

import pymysql
from meilisearch import Client
from meilisearch.errors import MeilisearchError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Batch size for Meilisearch add_documents
BATCH_SIZE = 5000


def _get_mysql_connection():
    """Create a MySQL connection from settings. Secrets via get_secret_value()."""
    settings = get_settings()
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD.get_secret_value(),
        database=settings.MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _get_meilisearch_client() -> Client:
    """Create Meilisearch client from settings. Secrets via get_secret_value()."""
    settings = get_settings()
    return Client(
        settings.MEILISEARCH_URL,
        api_key=settings.MEILISEARCH_MASTER_KEY.get_secret_value(),
    )


def _get_translations_for_game(conn: pymysql.Connection, game_slug: str) -> dict[str, list[str]]:
    """
    Load all translations for a game from card_translations.
    Returns: { entity_id: ["Nome IT", "Nome FR", ...] }.
    Called once per game at the start of each _index_*_prints for bulk fetch.
    """
    translations: dict[str, list[str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT entity_id, translated_name
            FROM card_translations
            WHERE game_slug = %s AND translated_name IS NOT NULL AND translated_name != ''
            """,
            (game_slug,),
        )
        for row in cur.fetchall():
            eid = (row["entity_id"] or "").strip()
            t_name = (row["translated_name"] or "").strip()
            if not eid or not t_name:
                continue
            if eid not in translations:
                translations[eid] = []
            if t_name not in translations[eid]:
                translations[eid].append(t_name)
    return translations


def _build_keywords_localized(original_name: str, trans_list: list[str]) -> list[str]:
    """Original name first, then translations, no duplicates."""
    keywords = [original_name] if original_name else []
    for t in trans_list or []:
        if t and t not in keywords:
            keywords.append(t)
    return keywords


def _clean_image_path(raw_path: str | None) -> str:
    """
    Rimuove il prefisso legacy /img/ o img/ dal path immagine.
    Su S3 le immagini sono salvate senza quel prefisso (es: cards/1/123.jpg).
    Usata per MTG, OP, PK e Sealed.
    """
    raw = (raw_path or "").strip()
    if raw.startswith("/img/"):
        return raw.replace("/img/", "", 1)
    if raw.startswith("img/"):
        return raw.replace("img/", "", 1)
    return raw


def _parse_available_languages(raw: Any) -> list[str]:
    """Parse available_languages from DB (JSON string, bytes, or list). Per pagina dettaglio MTG."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            import json
            out = json.loads(raw)
            return [str(x) for x in out] if isinstance(out, list) else []
        except Exception:
            return []
    return []

def _format_release_date(raw: Any) -> str | None:
    """Normalize DB date/datetime/string values to YYYY-MM-DD."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        # Accept already normalized values or datetime-like strings.
        return raw[:10]
    return None


def _index_mtg_prints(
    conn: pymysql.Connection,
    client: Client,
    index_name: str,
    batch_size: int,
) -> int:
    """Index MTG prints from cards_prints JOIN sets, cards, games. Entity = oracle_id."""
    logger.info("Fetching MTG translations from card_translations...")
    trans_map = _get_translations_for_game(conn, "mtg")

    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                cp.id AS print_id,
                cp.cardtrader_id,
                cp.oracle_id,
                COALESCE(c.name, '') AS printed_name,
                cp.image_path,
                COALESCE(s.name, '') AS set_name,
                s.code AS set_code,
                s.release_date,
                s.set_icon_uri,
                COALESCE(g.slug, 'mtg') AS game_slug,
                cp.collector_number,
                cp.rarity,
                cp.available_languages
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
            cardtrader_id = row.get("cardtrader_id")
            oracle_id = row["oracle_id"] or ""
            printed_name = (row["printed_name"] or "").strip() or "Unknown"
            image_path = _clean_image_path(row.get("image_path"))
            set_name = (row["set_name"] or "").strip()
            set_code = (row.get("set_code") or "").strip()
            release_date = _format_release_date(row.get("release_date"))
            set_icon_uri = (row.get("set_icon_uri") or "").strip() or None
            game_slug = (row["game_slug"] or "mtg").strip()
            collector_number = row.get("collector_number")
            rarity = row.get("rarity")
            available_languages = _parse_available_languages(row.get("available_languages"))

            keywords_localized = _build_keywords_localized(
                printed_name, trans_map.get(oracle_id, [])
            )

            doc = {
                "id": f"mtg_{print_id}",
                "name": printed_name,
                "set_name": set_name,
                "set_code": set_code,
                "release_date": release_date,
                "set_icon_uri": set_icon_uri,
                "game_slug": game_slug,
                "category_id": 1,
                "category_name": "Carta Singola",
                "image": image_path,
                "keywords_localized": keywords_localized,
            }
            if cardtrader_id is not None:
                doc["cardtrader_id"] = int(cardtrader_id)
            if collector_number is not None and str(collector_number).strip():
                doc["collector_number"] = str(collector_number).strip()
            if rarity is not None and str(rarity).strip():
                doc["rarity"] = str(rarity).strip()
            if available_languages:
                doc["available_languages"] = available_languages
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


def _index_op_prints(
    conn: pymysql.Connection,
    client: Client,
    index_name: str,
    batch_size: int,
) -> int:
    """Index One Piece prints from op_prints JOIN op_cards, sets, games. Entity = card_id. Nessuna gestione lingue (solo MTG)."""
    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                op.id AS print_id,
                op.cardtrader_id,
                COALESCE(oc.name_en, '') AS printed_name,
                op.image_path,
                COALESCE(s.name, '') AS set_name,
                s.code AS set_code,
                s.release_date,
                s.set_icon_uri,
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
            cardtrader_id = row.get("cardtrader_id")
            printed_name = (row["printed_name"] or "").strip() or "Unknown"
            image_path = _clean_image_path(row.get("image_path"))
            set_name = (row["set_name"] or "").strip()
            set_code = (row.get("set_code") or "").strip()
            release_date = _format_release_date(row.get("release_date"))
            set_icon_uri = (row.get("set_icon_uri") or "").strip() or None
            game_slug = (row["game_slug"] or "op").strip()

            doc = {
                "id": f"op_{print_id}",
                "name": printed_name,
                "set_name": set_name,
                "set_code": set_code,
                "release_date": release_date,
                "set_icon_uri": set_icon_uri,
                "game_slug": game_slug,
                "category_id": 1,
                "category_name": "Carta Singola",
                "image": image_path,
            }
            if cardtrader_id is not None:
                doc["cardtrader_id"] = int(cardtrader_id)
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


def _index_pk_prints(
    conn: pymysql.Connection,
    client: Client,
    index_name: str,
    batch_size: int,
) -> int:
    """Index Pokémon prints from pk_prints JOIN pk_cards, sets, games. Entity = card_id. Immagine da image_url. Nessuna gestione lingue (solo MTG)."""
    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                pp.id AS print_id,
                pp.cardtrader_id,
                COALESCE(pc.name_en, '') AS printed_name,
                pp.image_url AS image_path,
                COALESCE(s.name, '') AS set_name,
                s.code AS set_code,
                s.release_date,
                s.set_icon_uri,
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
            cardtrader_id = row.get("cardtrader_id")
            printed_name = (row["printed_name"] or "").strip() or "Unknown"
            image_path = _clean_image_path(row.get("image_path"))
            set_name = (row["set_name"] or "").strip()
            set_code = (row.get("set_code") or "").strip()
            release_date = _format_release_date(row.get("release_date"))
            set_icon_uri = (row.get("set_icon_uri") or "").strip() or None
            game_slug = (row["game_slug"] or "pk").strip()

            doc = {
                "id": f"pk_{print_id}",
                "name": printed_name,
                "set_name": set_name,
                "set_code": set_code,
                "release_date": release_date,
                "set_icon_uri": set_icon_uri,
                "game_slug": game_slug,
                "category_id": 1,
                "category_name": "Carta Singola",
                "image": image_path,
            }
            if cardtrader_id is not None:
                doc["cardtrader_id"] = int(cardtrader_id)
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


def _index_sealed_products(
    conn: pymysql.Connection,
    client: Client,
    index_name: str,
    batch_size: int,
) -> int:
    """Index sealed products (box, bustine, mazzi) from sealed_products JOIN sets, games. Excludes category_id 1 (singles)."""
    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                sp.id AS product_id,
                sp.cardtrader_id,
                COALESCE(sp.name_en, sp.name_it, '') AS name,
                COALESCE(sp.category_id, 0) AS category_id,
                sp.image_path,
                COALESCE(s.name, '') AS set_name,
                s.code AS set_code,
                s.release_date,
                s.set_icon_uri,
                COALESCE(g.slug, '') AS game_slug
            FROM sealed_products sp
            INNER JOIN sets s ON s.id = sp.set_id
            INNER JOIN games g ON g.id = s.game_id
            WHERE sp.category_id != 1
            ORDER BY sp.id
            """
        )
        batch: list[dict[str, Any]] = []
        for row in cur:
            product_id = row["product_id"]
            cardtrader_id = row.get("cardtrader_id")
            name = (row["name"] or "").strip() or "Unknown"
            category_id = row["category_id"]
            image_path = _clean_image_path(row.get("image_path"))
            set_name = (row["set_name"] or "").strip()
            set_code = (row.get("set_code") or "").strip()
            release_date = _format_release_date(row.get("release_date"))
            set_icon_uri = (row.get("set_icon_uri") or "").strip() or None
            game_slug = (row["game_slug"] or "").strip()

            doc = {
                "id": f"sealed_{product_id}",
                "name": name,
                "set_name": set_name,
                "set_code": set_code,
                "release_date": release_date,
                "set_icon_uri": set_icon_uri,
                "game_slug": game_slug,
                "category_id": category_id,
                "image": image_path,
            }
            if cardtrader_id is not None:
                doc["cardtrader_id"] = int(cardtrader_id)
            batch.append(doc)
            if len(batch) >= batch_size:
                client.index(index_name).add_documents(batch)
                count += len(batch)
                logger.info("Indexed sealed batch: %d docs (total so far: %d)", len(batch), count)
                batch = []

        if batch:
            client.index(index_name).add_documents(batch)
            count += len(batch)
            logger.info("Indexed final sealed batch: %d docs (total: %d)", len(batch), count)
    return count


def _configure_meilisearch_index(client: Client, index_name: str) -> None:
    """Searchable: name, keywords_localized, set_name. Filterable: id, cardtrader_id, game_slug, category_id, set_name, release_date, rarity. Sortable: name, set_name, release_date."""
    index = client.index(index_name)
    index.update_searchable_attributes(
        ["name", "keywords_localized", "set_name"]
    )
    index.update_filterable_attributes(["id", "cardtrader_id", "game_slug", "category_id", "set_name", "release_date", "rarity"])
    index.update_sortable_attributes(["name", "set_name", "release_date"])


def run_indexer() -> dict[str, Any]:
    """
    Full reindex: load translations per game from card_translations, index MTG/OP/PK, configure Meilisearch.
    Returns a summary with counts and any error message.
    """
    settings = get_settings()
    index_name = settings.MEILISEARCH_INDEX_NAME
    batch_size = settings.INDEXER_BATCH_SIZE or BATCH_SIZE
    result: dict[str, Any] = {
        "mtg": 0,
        "op": 0,
        "pk": 0,
        "sealed": 0,
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
        try:
            client.get_index(index_name)
        except MeilisearchError:
            client.create_index(index_name, {"primaryKey": "id"})

        result["mtg"] = _index_mtg_prints(conn, client, index_name, batch_size)
        result["op"] = _index_op_prints(conn, client, index_name, batch_size)
        result["pk"] = _index_pk_prints(conn, client, index_name, batch_size)
        result["sealed"] = _index_sealed_products(conn, client, index_name, batch_size)
        result["total"] = result["mtg"] + result["op"] + result["pk"] + result["sealed"]

        _configure_meilisearch_index(client, index_name)
        logger.info(
            "Reindex complete: mtg=%d op=%d pk=%d sealed=%d total=%d",
            result["mtg"], result["op"], result["pk"], result["sealed"], result["total"],
        )
    except Exception as e:
        logger.exception("Indexer failed")
        result["error"] = str(e)
    finally:
        conn.close()

    return result
