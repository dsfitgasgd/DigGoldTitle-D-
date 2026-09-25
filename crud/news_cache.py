from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func,update

from cache.news_cache import get_cached_categories, set_cache_categories, get_cache_news_list, set_cache_news_list
from models.news import Category, News
from schemas.base import NewsItemBase


async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    # 先尝试从缓存获取数据
    cached_categories = await get_cached_categories()
    if cached_categories:
        return cached_categories

    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    # 写入缓存
    if categories:
        categories = jsonable_encoder(categories)
        await set_cache_categories(categories)

    # 返回数据
    return categories


async def get_news_list(db: AsyncSession, category_id: int, skip: int = 0, limit: int = 100):
    # 先尝试从缓存获取新闻列表
    # 跳过的数量skip =(页码 -1)* 每页数量 →页码=跳过的数量 //每页数量+1
    # await get_cache_news_list(分类id,页码,每页数量)
    page = skip // limit + 1
    cached_list = await get_cache_news_list(category_id, page, limit)
    if cached_list:
        # 要的是 ORM
        return [News(**item) for item in cached_list]

    #查询的是指定分类下的所有新闻
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    news_list = result.scalars().all()

    #写入缓存
    if news_list:
        # 先把 ORM 数据 转换 字典才能写入缓存
        # ORM 转为 Pydantic, 再转为字典
        # by_alias=False 不使用别名，保持python风格，因为Redis数据是给后端用的
        news_data = [NewsItemBase.model_validate(item).model_dump(mode='json',by_alias=False) for item in news_list]
        await set_cache_news_list(category_id, page, limit, news_data)

    return news_list


async def get_news_count(db: AsyncSession, category_id: int):
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_news_detail(db: AsyncSession, news_id: int):
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def increase_view_news(db: AsyncSession, news_id: int):
    stmt = update(News).where(News.id == news_id).values(views=News.views + 1)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def get_related_news(db: AsyncSession, category_id: int, news_id: int,limit: int = 5):
    stmt = select(News).where(
        News.category_id == category_id,
        News.id != news_id
    ).where().order_by(
        News.views.desc(), #默认升序
        News.publish_time.asc()
    ).limit(limit)
    result = await db.execute(stmt)
    related_news = result.scalars().all()
    return [{
        "id": news_detail.id,
        "title": news_detail.title,
        "content": news_detail.content,
        "image": news_detail.image,
        "author": news_detail.author,
        "publishTime": news_detail.publish_time,
        "categoryId": news_detail.category_id,
        "views": news_detail.views
    } for news_detail in related_news]

