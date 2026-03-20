import uuid
from typing import Any, Iterable

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.models.semantic_relationship import SemanticRelationship

try:
    from neo4j import AsyncGraphDatabase
except Exception:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore


def _parse_domain_and_skills(semantic_items: list[tuple[str, dict]]) -> tuple[str | None, list[str]]:
    domain: str | None = None
    skills: list[str] = []
    for k, v in semantic_items:
        if k == "domain" and isinstance(v, dict):
            d = v.get("domain")
            if isinstance(d, str) and d.strip():
                domain = d.strip()
        if k == "skills" and isinstance(v, dict):
            s = v.get("skills")
            if isinstance(s, list):
                for item in s:
                    if isinstance(item, str) and item.strip() and item not in skills:
                        skills.append(item.strip())
    return domain, skills


class RelationshipRepo:
    async def upsert_relationships(
        self,
        *,
        user_id: uuid.UUID,
        semantic_items: list[tuple[str, dict]],
        source_extraction_id: uuid.UUID,
    ) -> None:
        raise NotImplementedError


class PostgresRelationshipRepo(RelationshipRepo):
    async def upsert_relationships(
        self,
        *,
        user_id: uuid.UUID,
        semantic_items: list[tuple[str, dict]],
        source_extraction_id: uuid.UUID,
    ) -> None:
        domain, skills = _parse_domain_and_skills(semantic_items)
        if not domain or not skills:
            return

        # Idempotency per extraction.
        await self._delete_by_extraction(user_id=user_id, source_extraction_id=source_extraction_id)

        # Represent (User)-[:HAS_SKILL]->(Skill) and (Skill)-[:ASSOCIATED_WITH]->(Domain).
        edges: list[dict[str, Any]] = []
        for skill in skills:
            edges.append(
                {
                    "user_id": user_id,
                    "from_key": "user",
                    "from_value": str(user_id),
                    "to_key": "skill",
                    "to_value": skill,
                    "relation_type": "HAS_SKILL",
                    "source_extraction_id": source_extraction_id,
                }
            )
            edges.append(
                {
                    "user_id": user_id,
                    "from_key": "skill",
                    "from_value": skill,
                    "to_key": "domain",
                    "to_value": domain,
                    "relation_type": "ASSOCIATED_WITH",
                    "source_extraction_id": source_extraction_id,
                }
            )

        await self._bulk_insert(edges)

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _delete_by_extraction(self, *, user_id: uuid.UUID, source_extraction_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(SemanticRelationship).where(
                SemanticRelationship.user_id == user_id,
                SemanticRelationship.source_extraction_id == source_extraction_id,
            )
        )

    async def _bulk_insert(self, edges: list[dict[str, Any]]) -> None:
        if not edges:
            return
        stmt = pg_insert(SemanticRelationship).values(edges)
        await self.session.execute(stmt)


class Neo4jRelationshipRepo(RelationshipRepo):
    def __init__(self):
        if AsyncGraphDatabase is None:
            raise RuntimeError("neo4j package not available")
        if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
            raise RuntimeError("Neo4j connection settings missing")

        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def upsert_relationships(
        self,
        *,
        user_id: uuid.UUID,
        semantic_items: list[tuple[str, dict]],
        source_extraction_id: uuid.UUID,
    ) -> None:
        domain, skills = _parse_domain_and_skills(semantic_items)
        if not domain or not skills:
            return

        async with self.driver.session() as session:
            for skill in skills:
                await session.run(
                    """
                    MERGE (u:User {id: $user_id})
                    MERGE (s:Skill {name: $skill})
                    MERGE (d:Domain {name: $domain})
                    MERGE (u)-[r1:HAS_SKILL]->(s)
                    SET r1.source_extraction_id = $source_extraction_id
                    MERGE (s)-[r2:ASSOCIATED_WITH]->(d)
                    SET r2.source_extraction_id = $source_extraction_id
                    """,
                    user_id=str(user_id),
                    skill=skill,
                    domain=domain,
                    source_extraction_id=str(source_extraction_id),
                )


def get_relationship_repo(session: AsyncSession) -> RelationshipRepo:
    """
    Factory for selecting Neo4j vs Postgres fallback.
    """
    if settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password:
        try:
            return Neo4jRelationshipRepo()
        except Exception:
            # Fail open: Postgres fallback ensures relationships are still created.
            return PostgresRelationshipRepo(session)
    return PostgresRelationshipRepo(session)

