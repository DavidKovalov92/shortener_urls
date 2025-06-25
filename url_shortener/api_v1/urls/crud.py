from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List
import string
import random
from datetime import datetime, timedelta

from models.url_model import URL, Tags, url_tag_association
from schemas.url_schemas import URLCreate, URLUpdate, TagCreate, URLStats, URLFilter, ExportFormat


def generate_short_code(length: int = 6) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


async def create_url(db: AsyncSession, url: URLCreate, owner_id: int) -> URL:
    short_code = url.short_code
    if not short_code:
        while True:
            short_code = generate_short_code()
            existing = await get_url_by_short_code(db, short_code)
            if not existing:
                break
    else:
        existing = await get_url_by_short_code(db, short_code)
        if existing:
            raise ValueError("Short code already exists")
    
    db_url = URL(
        original_url=str(url.original_url),
        short_code=short_code,
        owner_id=owner_id
    )
    db.add(db_url)
    await db.commit()
    await db.refresh(db_url)
    
    if url.tags:
        await add_tags_to_url(db, db_url.id, url.tags)
    
    return db_url


async def get_url_by_id(db: AsyncSession, url_id: int) -> Optional[URL]:
    result = await db.execute(
        select(URL).options(selectinload(URL.tags)).where(URL.id == url_id)
    )
    return result.scalar_one_or_none()


async def get_url_by_short_code(db: AsyncSession, short_code: str) -> Optional[URL]:
    result = await db.execute(
        select(URL).options(selectinload(URL.tags)).where(URL.short_code == short_code)
    )
    return result.scalar_one_or_none()


async def get_user_urls(
    db: AsyncSession, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None
) -> tuple[List[URL], int]:
    query = select(URL).options(selectinload(URL.tags)).where(URL.owner_id == user_id)
    
    if search:
        query = query.where(
            URL.original_url.contains(search) | 
            URL.short_code.contains(search)
        )
    
    count_query = select(func.count(URL.id)).where(URL.owner_id == user_id)
    if search:
        count_query = count_query.where(
            URL.original_url.contains(search) | 
            URL.short_code.contains(search)
        )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(desc(URL.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    urls = result.scalars().all()
    
    return list(urls), total


async def update_url(db: AsyncSession, url_id: int, url_update: URLUpdate, owner_id: int) -> Optional[URL]:
    url = await get_url_by_id(db, url_id)
    if not url or url.owner_id != owner_id:
        return None
    
    if url_update.original_url:
        url.original_url = str(url_update.original_url)
    
    if url_update.tags is not None:
        await db.execute(
            url_tag_association.delete().where(url_tag_association.c.url_id == url_id)
        )
        if url_update.tags:
            await add_tags_to_url(db, url_id, url_update.tags)
    
    await db.commit()
    await db.refresh(url)
    return url


async def delete_url(db: AsyncSession, url_id: int, owner_id: int) -> bool:
    url = await get_url_by_id(db, url_id)
    if not url or url.owner_id != owner_id:
        return False
    
    await db.delete(url)
    await db.commit()
    return True


async def increment_click_count(db: AsyncSession, short_code: str) -> Optional[URL]:
    url = await get_url_by_short_code(db, short_code)
    if not url:
        return None
    
    url.click_count += 1
    await db.commit()
    return url

async def increment_click_count_always(db: AsyncSession, short_code: str) -> Optional[URL]:
    """Завжди рахує клік, навіть якщо URL не знайдено"""
    url = await get_url_by_short_code(db, short_code)
    if url:
        url.click_count += 1
        await db.commit()
    return url

async def create_tag(db: AsyncSession, tag: TagCreate) -> Tags:
    db_tag = Tags(name=tag.name.lower().strip())
    db.add(db_tag)
    await db.commit()
    await db.refresh(db_tag)
    return db_tag


async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[Tags]:
    result = await db.execute(select(Tags).where(Tags.name == name.lower().strip()))
    return result.scalar_one_or_none()


async def get_or_create_tag(db: AsyncSession, name: str) -> Tags:
    tag = await get_tag_by_name(db, name)
    if not tag:
        tag = await create_tag(db, TagCreate(name=name))
    return tag


async def add_tags_to_url(db: AsyncSession, url_id: int, tag_names: List[str]) -> None:
    for tag_name in tag_names:
        if tag_name.strip():
            tag = await get_or_create_tag(db, tag_name)
            existing = await db.execute(
                select(url_tag_association).where(
                    and_(
                        url_tag_association.c.url_id == url_id,
                        url_tag_association.c.tag_id == tag.id
                    )
                )
            )
            if not existing.first():
                await db.execute(
                    url_tag_association.insert().values(url_id=url_id, tag_id=tag.id)
                )
    await db.commit()


async def get_user_tags(db: AsyncSession, user_id: int) -> List[Tags]:
    result = await db.execute(
        select(Tags)
        .join(url_tag_association)
        .join(URL)
        .where(URL.owner_id == user_id)
        .distinct()
        .order_by(Tags.name)
    )
    return list(result.scalars().all())


async def delete_tag(db: AsyncSession, tag_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(Tags)
        .join(url_tag_association)
        .join(URL)
        .where(and_(Tags.id == tag_id, URL.owner_id == user_id))
    )
    tag = result.scalar_one_or_none()
    
    if not tag:
        return False
    
    await db.execute(
        url_tag_association.delete().where(
            url_tag_association.c.tag_id == tag_id
        )
    )
    
    other_usage = await db.execute(
        select(func.count(url_tag_association.c.url_id))
        .where(url_tag_association.c.tag_id == tag_id)
    )
    
    if other_usage.scalar() == 0:
        await db.delete(tag)
    
    await db.commit()
    return True


async def get_url_stats(db: AsyncSession, user_id: int) -> List[URLStats]:
    result = await db.execute(
        select(URL)
        .where(URL.owner_id == user_id)
        .order_by(desc(URL.click_count))
    )
    urls = result.scalars().all()
    
    stats = []
    for url in urls:
        stats.append(URLStats(
            url_id=url.id,
            short_code=url.short_code,
            original_url=url.original_url,
            click_count=url.click_count,
            created_at=url.created_at,
        ))
    
    return stats


async def get_top_urls(db: AsyncSession, user_id: int, limit: int = 10) -> List[URL]:
    result = await db.execute(
        select(URL)
        .options(selectinload(URL.tags))
        .where(URL.owner_id == user_id)
        .order_by(desc(URL.click_count))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_total_stats(db: AsyncSession, user_id: int) -> dict:
    urls_count = await db.execute(
        select(func.count(URL.id)).where(URL.owner_id == user_id)
    )
    total_urls = urls_count.scalar() or 0
    
    clicks_count = await db.execute(
        select(func.sum(URL.click_count)).where(URL.owner_id == user_id)
    )
    total_clicks = clicks_count.scalar() or 0
    
    last_month = datetime.utcnow() - timedelta(days=30)
    recent_urls = await db.execute(
        select(func.count(URL.id))
        .where(and_(URL.owner_id == user_id, URL.created_at >= last_month))
    )
    recent_urls_count = recent_urls.scalar() or 0
    
    return {
        "total_urls": total_urls,
        "total_clicks": total_clicks,
        "recent_urls": recent_urls_count,
        "avg_clicks_per_url": round(total_clicks / total_urls, 2) if total_urls > 0 else 0
    }



async def search_and_filter_urls(
    db: AsyncSession, 
    user_id: int, 
    filters: URLFilter,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[URL], int]:
    query = select(URL).options(selectinload(URL.tags)).where(URL.owner_id == user_id)
    
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.where(
            URL.original_url.ilike(search_term) | 
            URL.short_code.ilike(search_term)
        )
    
    if filters.tags:
        query = query.join(URL.tags).where(Tags.name.in_(filters.tags))
    
    if filters.min_clicks is not None:
        query = query.where(URL.click_count >= filters.min_clicks)
    if filters.max_clicks is not None:
        query = query.where(URL.click_count <= filters.max_clicks)
    
    if filters.date_from:
        query = query.where(URL.created_at >= filters.date_from)
    if filters.date_to:
        query = query.where(URL.created_at <= filters.date_to)
    
    count_query = select(func.count(URL.id)).where(URL.owner_id == user_id)
    if filters.search:
        search_term = f"%{filters.search}%"
        count_query = count_query.where(
            URL.original_url.ilike(search_term) | 
            URL.short_code.ilike(search_term)
        )
    if filters.tags:
        count_query = count_query.join(URL.tags).where(Tags.name.in_(filters.tags))
    if filters.min_clicks is not None:
        count_query = count_query.where(URL.click_count >= filters.min_clicks)
    if filters.max_clicks is not None:
        count_query = count_query.where(URL.click_count <= filters.max_clicks)
    if filters.date_from:
        count_query = count_query.where(URL.created_at >= filters.date_from)
    if filters.date_to:
        count_query = count_query.where(URL.created_at <= filters.date_to)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    if filters.sort_by == "click_count":
        if filters.sort_order == "asc":
            query = query.order_by(URL.click_count)
        else:
            query = query.order_by(desc(URL.click_count))
    elif filters.sort_by == "short_code":
        if filters.sort_order == "asc":
            query = query.order_by(URL.short_code)
        else:
            query = query.order_by(desc(URL.short_code))
    else:
        if filters.sort_order == "asc":
            query = query.order_by(URL.created_at)
        else:
            query = query.order_by(desc(URL.created_at))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    urls = result.scalars().all()
    
    return list(urls), total


async def get_advanced_stats(db: AsyncSession, user_id: int, filters: Optional[URLFilter] = None) -> dict:
    query = select(URL).where(URL.owner_id == user_id)
    
    # Застосування фільтрів
    if filters:
        if filters.tags:
            query = query.join(URL.tags).where(Tags.name.in_(filters.tags))
        if filters.date_from:
            query = query.where(URL.created_at >= filters.date_from)
        if filters.date_to:
            query = query.where(URL.created_at <= filters.date_to)
    
    result = await db.execute(query)
    urls = result.scalars().all()
    
    if not urls:
        return {
            "total_urls": 0,
            "total_clicks": 0,
            "avg_clicks_per_url": 0,
            "most_clicked_url": None,
            "clicks_by_date": []
        }
    
    total_clicks = sum(url.click_count for url in urls)
    most_clicked = max(urls, key=lambda x: x.click_count) if urls else None
    
    clicks_by_date = []
    for i in range(30):
        date = datetime.utcnow().date() - timedelta(days=i)
        clicks_on_date = sum(
            url.click_count for url in urls 
            if url.created_at.date() == date
        )
        clicks_by_date.append({
            "date": date.isoformat(),
            "clicks": clicks_on_date
        })
    
    return {
        "total_urls": len(urls),
        "total_clicks": total_clicks,
        "avg_clicks_per_url": round(total_clicks / len(urls), 2) if urls else 0,
        "most_clicked_url": {
            "id": most_clicked.id,
            "short_code": most_clicked.short_code,
            "original_url": most_clicked.original_url,
            "click_count": most_clicked.click_count
        } if most_clicked else None,
        "clicks_by_date": clicks_by_date
    }


async def export_user_urls(
    db: AsyncSession, 
    user_id: int, 
    format_type: ExportFormat,
    filters: Optional[URLFilter] = None
) -> dict:  
    if filters:
        urls, _ = await search_and_filter_urls(db, user_id, filters, skip=0, limit=10000)
    else:
        urls, _ = await get_user_urls(db, user_id, skip=0, limit=10000)
    
    export_data = []
    for url in urls:
        url_data = {
            "id": url.id,
            "original_url": url.original_url,
            "short_code": url.short_code,
            "short_url": f"http://localhost:8000/r/{url.short_code}",
            "click_count": url.click_count,
            "created_at": url.created_at.isoformat(),
            "updated_at": url.updated_at.isoformat() if url.updated_at else None,
            "tags": [tag.name for tag in url.tags] if url.tags else []
        }
        export_data.append(url_data)
    
    return {
        "format": format_type.value,
        "data": export_data,
        "total_records": len(export_data),
        "exported_at": datetime.utcnow().isoformat(),
        "filters_applied": filters.dict() if filters else None
    } 