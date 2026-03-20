import re
import json
from typing import Any


from utils.embeddings import get_embeddings

def _safe_str(v: Any) -> str | None:
    if isinstance(v, str):
        s = " ".join(v.split())
        return s or None
    return None


def _safe_list_strings(v: Any) -> list[str]:
    if not isinstance(v, list):
        return []
    out: list[str] = []
    for item in v:
        s = _safe_str(item)
        if s and s not in out:
            out.append(s)
    return out


def infer_domain(role: str | None, skills: list[str]) -> str:
    r = (role or "").lower()
    skill_join = " ".join(skills).lower()

    if any(k in r for k in ["software", "engineer", "developer"]) or any(
        k in skill_join for k in ["python", "java", "javascript", "typescript", "go", "c++"]
    ):
        return "software_engineering"
    if any(k in r for k in ["data scientist", "ml", "machine learning", "ai"]) or any(
        k in skill_join for k in ["ml", "machine learning", "ai", "pytorch", "tensorflow"]
    ):
        return "data_science_ai"
    return "general"


async def extract_semantic_items(
    engine_result: dict[str, Any],
) -> list[tuple[str, dict, list[float] | None]]:
    """
    Deterministic semantic extraction from the engine's structured output.
    Now includes async embedding generation for each item.
    """
    data = engine_result.get("data") if isinstance(engine_result, dict) else None
    if not isinstance(data, dict):
        return []

    name = _safe_str(data.get("name"))
    role = _safe_str(data.get("role"))
    skills = _safe_list_strings(data.get("skills"))
    experience_years = data.get("experience_years")
    education = _safe_str(data.get("education"))
    summary = _safe_str(data.get("summary"))

    domain = infer_domain(role, skills)

    temp_items: list[tuple[str, dict]] = []
    if name:
        temp_items.append(("name", {"name": name}))
    if role:
        temp_items.append(("role", {"role": role}))
    if skills:
        temp_items.append(("skills", {"skills": skills}))
    if experience_years is not None:
        if isinstance(experience_years, (int, float)) and experience_years == int(experience_years):
            temp_items.append(("experience_years", {"years": int(experience_years)}))
        elif isinstance(experience_years, str):
            m = re.search(r"\d+", experience_years)
            if m:
                temp_items.append(("experience_years", {"years": int(m.group(0))}))
    if education:
        temp_items.append(("education", {"education": education}))
    if summary:
        temp_items.append(("summary", {"summary": summary}))
    temp_items.append(("domain", {"domain": domain}))

    # Generate embeddings for everything in batch
    texts_to_embed = [f"{k}: {json.dumps(v)}" for k, v in temp_items]
    embeddings = await get_embeddings(texts_to_embed)
    
    final_items = []
    for i, (k, v) in enumerate(temp_items):
        emb = embeddings[i] if i < len(embeddings) else None
        final_items.append((k, v, emb))
        
    return final_items

