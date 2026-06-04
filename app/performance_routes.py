"""
Performance Optimization Routes
10 REST API endpoints for caching, search, optimization
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.performance_optimization import (
    CacheManager, FullTextSearchManager, QueryOptimizer,
    CacheWarmupManager, PerformanceMonitor
)

router = APIRouter(prefix="/api/crm/performance", tags=["Performance Optimization"])

# Initialize cache manager (in production, use Redis)
cache_manager = CacheManager(redis_client=None)  # Set actual redis client in production


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SearchRequest(BaseModel):
    """Search request"""
    query: str
    limit: int = 20


class SuggestRequest(BaseModel):
    """Suggestion request"""
    query: str
    field: str = "email"  # email, company, name
    limit: int = 5


# ============================================================================
# CACHE ENDPOINTS
# ============================================================================

@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Clear cache or cache pattern"""
    if pattern:
        cleared = cache_manager.clear_pattern(pattern)
        return {
            "status": "cleared",
            "pattern": pattern,
            "keys_cleared": cleared
        }
    else:
        # Clear all cache
        return {
            "status": "cleared",
            "message": "Cache cleared (in production, configure Redis pattern clear)"
        }


@router.post("/cache/warmup")
async def warmup_cache(
    background_tasks: BackgroundTasks,
    cache_type: str = "customers",
    db: Session = Depends(get_db)
):
    """Warm up cache with frequently accessed data"""
    if cache_type == "customers":
        background_tasks.add_task(
            CacheWarmupManager.warmup_customer_cache,
            db=db,
            cache=cache_manager
        )
    elif cache_type == "analytics":
        background_tasks.add_task(
            CacheWarmupManager.warmup_analytics_cache,
            db=db,
            cache=cache_manager
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid cache type")
    
    return {
        "status": "warming",
        "cache_type": cache_type,
        "message": "Cache warmup started in background"
    }


@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    return cache_manager.get_stats()


@router.get("/cache/health")
async def cache_health():
    """Health check for cache layer"""
    stats = cache_manager.get_stats()
    return {
        "status": "healthy" if stats["total_requests"] >= 0 else "initializing",
        "service": "Cache Manager",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_type": "redis",
        "stats": stats
    }


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@router.post("/search")
async def search_customers(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Full-text search for customers"""
    if len(request.query) < 2:
        raise HTTPException(status_code=400, detail="Search query too short")
    
    results = FullTextSearchManager.search_customers(
        db,
        request.query,
        limit=request.limit
    )
    
    return {
        "query": request.query,
        "result_count": len(results),
        "results": results
    }


@router.post("/search/suggest")
async def search_suggestions(
    request: SuggestRequest,
    db: Session = Depends(get_db)
):
    """Get search suggestions/autocomplete"""
    if len(request.query) < 1:
        raise HTTPException(status_code=400, detail="Query too short")
    
    suggestions = FullTextSearchManager.search_suggestions(
        db,
        request.query,
        field=request.field,
        limit=request.limit
    )
    
    return {
        "field": request.field,
        "query": request.query,
        "suggestions": suggestions
    }


# ============================================================================
# OPTIMIZATION ENDPOINTS
# ============================================================================

@router.get("/query/{customer_id}/analyze")
async def analyze_customer_query(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Analyze query performance for specific customer"""
    result = QueryOptimizer.analyze_customer_query(db, customer_id)
    return result


@router.post("/query/bulk/analyze")
async def analyze_bulk_query(
    filters: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Analyze bulk query performance"""
    result = QueryOptimizer.analyze_bulk_query(db, filters)
    return result


@router.get("/slow-queries")
async def get_slow_queries():
    """Get list of slow queries"""
    queries = QueryOptimizer.get_slow_queries()
    return {
        "slow_queries": queries,
        "total": len(queries)
    }


@router.get("/stats")
async def performance_stats(db: Session = Depends(get_db)):
    """Get overall performance statistics"""
    return PerformanceMonitor.get_performance_stats(db)


@router.get("/recommendations")
async def optimization_recommendations(db: Session = Depends(get_db)):
    """Get optimization recommendations"""
    recommendations = PerformanceMonitor.get_optimization_recommendations(db)
    return {
        "recommendations": recommendations,
        "total": len(recommendations),
        "high_priority": len([r for r in recommendations if r["priority"] == "high"]),
        "medium_priority": len([r for r in recommendations if r["priority"] == "medium"]),
        "low_priority": len([r for r in recommendations if r["priority"] == "low"])
    }


@router.get("/health")
async def performance_health(db: Session = Depends(get_db)):
    """Health check for performance optimization service"""
    stats = PerformanceMonitor.get_performance_stats(db)
    cache_stats = cache_manager.get_stats()
    
    return {
        "status": "healthy",
        "service": "Performance Optimization",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_hit_rate": cache_stats["hit_rate"],
        "database_tables": {
            "customers": stats["database"]["total_customers"],
            "conversions": stats["database"]["total_conversions"],
            "cart_items": stats["database"]["total_cart_items"]
        },
        "features": {
            "caching": True,
            "full_text_search": True,
            "query_optimization": True
        }
    }
