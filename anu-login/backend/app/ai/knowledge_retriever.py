"""Knowledge Base Retriever - Retrieve docs before AI replies

Prevents hallucinations by grounding AI in actual product/policy knowledge.
For Pureleven: products, shipping, return policy, ingredients, usage.
"""

import logging
from typing import Any, Optional

from app.storage import get_db_connection

logger = logging.getLogger(__name__)


def search(query: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Search knowledge base for relevant documents.
    Returns: {relevant_docs: [doc1, doc2, ...], has_match: bool}
    """
    
    if not query:
        return {"relevant_docs": [], "has_match": False}
    
    try:
        conn = get_db_connection()
        
        # Search in Shopify products (name, description, tags)
        products = conn.execute(
            """
            SELECT id, title, description, tags, price
            FROM shopify_products
            WHERE is_active = 1 AND (
                LOWER(title) LIKE ? OR
                LOWER(description) LIKE ? OR
                LOWER(tags) LIKE ?
            )
            LIMIT 5
            """,
            (f"%{query.lower()}%", f"%{query.lower()}%", f"%{query.lower()}%")
        ).fetchall()
        
        # Search in content (articles, blog posts)
        content = conn.execute(
            """
            SELECT id, title, body, content_type
            FROM shopify_content
            WHERE LOWER(title) LIKE ? OR LOWER(body) LIKE ?
            LIMIT 3
            """,
            (f"%{query.lower()}%", f"%{query.lower()}%")
        ).fetchall()
        
        docs = []
        
        # Format product docs
        for row in products:
            docs.append({
                "type": "product",
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "tags": row[3],
                "price": row[4],
            })
        
        # Format content docs
        for row in content:
            docs.append({
                "type": row[3],  # content_type
                "id": row[0],
                "title": row[1],
                "body": row[2][:500],  # Truncate for brevity
            })
        
        return {
            "relevant_docs": docs,
            "has_match": len(docs) > 0,
            "query": query,
        }
    except Exception as e:
        logger.error(f"Knowledge search failed: {e}")
        return {"relevant_docs": [], "has_match": False}


def add_context_to_prompt(prompt: str, docs: list[dict[str, Any]]) -> str:
    """
    Augment AI prompt with retrieved documents.
    Prevents AI from hallucinating by grounding in facts.
    """
    
    if not docs:
        return prompt
    
    # Build context string
    context = "\n\nRELEVANT INFORMATION FROM KNOWLEDGE BASE:\n"
    
    for i, doc in enumerate(docs[:3], 1):  # Use top 3 docs
        if doc["type"] == "product":
            context += f"\n{i}. Product: {doc['title']}\n"
            if doc.get('description'):
                context += f"   Details: {doc['description'][:200]}\n"
            if doc.get('price'):
                context += f"   Price: ₹{doc['price']}\n"
        else:
            context += f"\n{i}. {doc['type'].title()}: {doc['title']}\n"
            if doc.get('body'):
                context += f"   {doc['body']}\n"
    
    context += "\nBase your answer on the above information. Do not make up facts."
    
    return prompt + context
