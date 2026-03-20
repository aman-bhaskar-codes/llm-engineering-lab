import logging
from typing import List, Dict, Any
from neo4j import GraphDatabase, AsyncGraphDatabase
from core.config import settings

logger = logging.getLogger(__name__)

class GraphMemory:
    """
    Relational Memory layer using Neo4j.
    Implements a 'fail-open' design for high availability in production.
    """
    def __init__(self):
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self.driver = None
        self._connected = False

    async def connect(self):
        try:
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            self._connected = True
            logger.info("Successfully connected to Neo4j Graph Database.")
        except Exception as e:
            self._connected = False
            logger.warning(f"Neo4j connection failed: {e}. Relational memory will be disabled (Fail-Open).")

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def save_extraction_relations(self, user_id: str, extraction_data: Dict[str, Any]):
        """
        Extracts and saves relationships from a successful extraction.
        Example: User -> HAS_SKILL -> Skill
        """
        if not self._connected:
            return

        try:
            async with self.driver.session() as session:
                name = extraction_data.get("name", "Unknown")
                role = extraction_data.get("role", "Unknown")
                skills = extraction_data.get("skills", [])
                if isinstance(skills, str):
                    skills = [skills]
                
                # Cypher query to build the graph
                # 1. Merge User node
                # 2. Merge Skill nodes and link them
                # 3. Merge Role as a property or node
                
                query = """
                MERGE (u:User {id: $user_id})
                SET u.name = $name, u.role = $role, u.last_updated = timestamp()
                
                WITH u
                UNWIND $skills as skill_name
                MERGE (s:Skill {name: skill_name})
                MERGE (u)-[:HAS_SKILL]->(s)
                
                RETURN count(s) as skill_count
                """
                
                await session.run(query, user_id=user_id, name=name, role=role, skills=skills)
                logger.info(f"GraphMemory: Saved relations for user {user_id}")
        except Exception as e:
            logger.error(f"GraphMemory Error while saving relations: {e}")

    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves relational context for a user to aid extraction accuracy.
        """
        if not self._connected:
            return {}

        try:
            async with self.driver.session() as session:
                query = """
                MATCH (u:User {id: $user_id})-[:HAS_SKILL]->(s:Skill)
                RETURN u.name as name, u.role as role, collect(s.name) as skills
                """
                result = await session.run(query, user_id=user_id)
                record = await result.single()
                if record:
                    return {
                        "name": record["name"],
                        "role": record["role"],
                        "skills": record["skills"]
                    }
                return {}
        except Exception as e:
            logger.error(f"GraphMemory Error while fetching context: {e}")
            return {}

# Global instance
graph_memory = GraphMemory()
