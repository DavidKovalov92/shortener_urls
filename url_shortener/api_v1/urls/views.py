from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from .dependencies import get_current_user, get_db
from .crud import (
    create_url, get_url_by_id, get_url_by_short_code, get_user_urls,
    update_url, delete_url, increment_click_count, increment_click_count_always, get_user_tags,
    get_url_stats, get_top_urls, get_total_stats, delete_tag,
    search_and_filter_urls, get_advanced_stats, export_user_urls
)
from schemas.url_schemas import (
    URLCreate, URLUpdate, URLResponse, URLListResponse, 
    TagResponse, URLStats, URLFilter, ExportFormat, ExportRequest
)
from models.user_model import User

router = APIRouter(prefix="/urls", tags=["URLs"])

@router.post("/", response_model=URLResponse)
async def create_short_url(
    url_data: URLCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        url = await create_url(db, url_data, current_user.id)
        url_with_tags = await get_url_by_id(db, url.id)
        return URLResponse(
            id=url_with_tags.id,
            original_url=url_with_tags.original_url,
            short_code=url_with_tags.short_code,
            click_count=url_with_tags.click_count,
            owner_id=url_with_tags.owner_id,
            created_at=url_with_tags.created_at,
            updated_at=url_with_tags.updated_at,
            tags=[tag.name for tag in url_with_tags.tags] if url_with_tags.tags else []
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/stats")
async def get_all_stats(
    stat_type: str = Query("overview", description="Тип статистики: overview, detailed, top, by-tags, by-date, advanced"),
    limit: int = Query(10, ge=1, le=50, description="Ліміт для топ URL"),
    days: int = Query(30, ge=1, le=365, description="Кількість днів для статистики по датах"),
    filters: Optional[str] = Query(None, description="JSON фільтри для продвинутої статистики"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    if stat_type == "overview":
        return await get_total_stats(db, current_user.id)
    
    elif stat_type == "detailed":
        return await get_url_stats(db, current_user.id)
    
    elif stat_type == "top":
        urls = await get_top_urls(db, current_user.id, limit)
        return [URLResponse(
            id=url.id,
            original_url=url.original_url,
            short_code=url.short_code,
            click_count=url.click_count,
            owner_id=url.owner_id,
            created_at=url.created_at,
            updated_at=url.updated_at,
            tags=[tag.name for tag in url.tags] if url.tags else []
        ) for url in urls]
    
    elif stat_type == "by-tags":
        tags = await get_user_tags(db, current_user.id)
        stats_by_tags = []
        
        for tag in tags:
            tag_filter = URLFilter(tags=[tag.name])
            urls, _ = await search_and_filter_urls(db, current_user.id, tag_filter, skip=0, limit=10000)
            
            total_clicks = sum(url.click_count for url in urls)
            stats_by_tags.append({
                "tag_name": tag.name,
                "urls_count": len(urls),
                "total_clicks": total_clicks,
                "avg_clicks_per_url": round(total_clicks / len(urls), 2) if urls else 0
            })
        
        stats_by_tags.sort(key=lambda x: x["total_clicks"], reverse=True)
        return {
            "stats_by_tags": stats_by_tags,
            "total_tags": len(stats_by_tags)
        }
    
    elif stat_type == "by-date":
        from datetime import datetime, timedelta
        
        stats_by_date = []
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=i)
            date_start = datetime.combine(date, datetime.min.time())
            date_end = datetime.combine(date, datetime.max.time())
            
            date_filter = URLFilter(date_from=date_start, date_to=date_end)
            urls, _ = await search_and_filter_urls(db, current_user.id, date_filter, skip=0, limit=10000)
            
            total_clicks = sum(url.click_count for url in urls)
            stats_by_date.append({
                "date": date.isoformat(),
                "urls_created": len(urls),
                "total_clicks": total_clicks
            })
        
        stats_by_date.sort(key=lambda x: x["date"], reverse=True)
        return {
            "stats_by_date": stats_by_date,
            "period_days": days
        }
    
    elif stat_type == "advanced":
        filter_obj = None
        if filters:
            try:
                import json
                filter_data = json.loads(filters)
                filter_obj = URLFilter(**filter_data)
            except Exception:
                pass
        
        return await get_advanced_stats(db, current_user.id, filter_obj)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stat_type. Available: overview, detailed, top, by-tags, by-date, advanced"
        )

@router.get("/", response_model=URLListResponse)
async def get_my_urls(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    urls, total = await get_user_urls(db, current_user.id, skip, limit, search)
    
    url_responses = []
    for url in urls:
        url_responses.append(URLResponse(
            id=url.id,
            original_url=url.original_url,
            short_code=url.short_code,
            click_count=url.click_count,
            owner_id=url.owner_id,
            created_at=url.created_at,
            updated_at=url.updated_at,
            tags=[tag.name for tag in url.tags] if url.tags else []
        ))
    
    return URLListResponse(
        urls=url_responses,
        total=total,
        page=skip // limit + 1,
        per_page=limit
    )

@router.get("/{url_id}", response_model=URLResponse)
async def get_url(
    url_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    url = await get_url_by_id(db, url_id)
    if not url or url.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found"
        )
    
    return URLResponse(
        id=url.id,
        original_url=url.original_url,
        short_code=url.short_code,
        click_count=url.click_count,
        owner_id=url.owner_id,
        created_at=url.created_at,
        updated_at=url.updated_at,
        tags=[tag.name for tag in url.tags] if url.tags else []
    )

@router.put("/{url_id}", response_model=URLResponse)
async def update_short_url(
    url_id: int,
    url_data: URLUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    url = await update_url(db, url_id, url_data, current_user.id)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found"
        )
    
    return URLResponse(
        id=url.id,
        original_url=url.original_url,
        short_code=url.short_code,
        click_count=url.click_count,
        owner_id=url.owner_id,
        created_at=url.created_at,
        updated_at=url.updated_at,
        tags=[tag.name for tag in url.tags] if url.tags else []
    )

@router.delete("/{url_id}")
async def delete_short_url(
    url_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    success = await delete_url(db, url_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found"
        )
    
    return {"message": "URL deleted successfully"}

@router.get("/tags/", response_model=List[TagResponse])
async def get_my_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tags = await get_user_tags(db, current_user.id)
    return [TagResponse(
        id=tag.id,
        name=tag.name,
        created_at=tag.created_at
    ) for tag in tags]

@router.delete("/tags/{tag_id}")
async def delete_user_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    success = await delete_tag(db, tag_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return {"message": "Tag deleted successfully"}


public_router = APIRouter(tags=["Public"])

@public_router.get("/r/{short_code}")
async def redirect_url(
    short_code: str,
    db: AsyncSession = Depends(get_db)
):
    url = await increment_click_count_always(db, short_code)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found"
        )
    
    return RedirectResponse(url=url.original_url, status_code=301)

@public_router.get("/info/{short_code}", response_model=URLResponse)
async def get_url_info(
    short_code: str,
    db: AsyncSession = Depends(get_db)
):
    url = await get_url_by_short_code(db, short_code)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL not found"
        )
    
    return URLResponse(
        id=url.id,
        original_url=url.original_url,
        short_code=url.short_code,
        click_count=url.click_count,
        owner_id=url.owner_id,
        created_at=url.created_at,
        updated_at=url.updated_at,
        tags=[tag.name for tag in url.tags] if url.tags else []
    )


@router.post("/search", response_model=URLListResponse)
async def advanced_search(
    filters: URLFilter,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    urls, total = await search_and_filter_urls(db, current_user.id, filters, skip, limit)
    
    url_responses = []
    for url in urls:
        url_responses.append(URLResponse(
            id=url.id,
            original_url=url.original_url,
            short_code=url.short_code,
            click_count=url.click_count,
            owner_id=url.owner_id,
            created_at=url.created_at,
            updated_at=url.updated_at,
            tags=[tag.name for tag in url.tags] if url.tags else []
        ))
    
    return URLListResponse(
        urls=url_responses,
        total=total,
        page=skip // limit + 1,
        per_page=limit
    )



@router.post("/export")
async def export_urls(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    export_data = await export_user_urls(
        db, 
        current_user.id, 
        export_request.format,
        export_request.filters
    )
    
    if export_request.format == ExportFormat.CSV:
        if export_data["data"]:
            headers = list(export_data["data"][0].keys())
            rows = []
            for item in export_data["data"]:
                row = []
                for header in headers:
                    value = item[header]
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    row.append(str(value) if value is not None else "")
                rows.append(row)
            
            export_data["csv_headers"] = headers
            export_data["csv_rows"] = rows
    
    return export_data 