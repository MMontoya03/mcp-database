import logging
from fastmcp import FastMCP
from sqlalchemy import select, func,text

from src.database import get_db_context
from src.models import (
    Actor,
    Customer,
    Film,
    Category,
    FilmCategory,
    FilmActor,
    Rental,
    Inventory,
    Payment
)

logger = logging.getLogger(__name__)

# Inicializar MCP
mcp = FastMCP("Pagila MCP Server")

@mcp.tool
async def get_customers() -> str:
    """Obtiene todos los clientes"""
    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(Customer.customer_id, Customer.first_name, Customer.last_name)
                .order_by(Customer.last_name)
            )

            customers = result.all()

            return str([
                {
                    "customer_id": c.customer_id,
                    "name": f"{c.first_name} {c.last_name}"
                } for c in customers
            ])
    except Exception as e:
        logger.error(e)
        return f"Error obteniendo clientes: {e}"


@mcp.tool
async def get_actors(limit: int = 20) -> str:
    """Lista actores"""
    async with get_db_context() as session:
        result = await session.execute(
            select(Actor.actor_id, Actor.first_name, Actor.last_name)
            .limit(limit)
        )
        actors = result.all()

        return str([
            {
                "actor_id": a.actor_id,
                "name": f"{a.first_name} {a.last_name}"
            } for a in actors
        ])

@mcp.tool
async def get_films(limit: int = 20) -> str:
    """Lista películas"""
    async with get_db_context() as session:
        result = await session.execute(
            select(Film.film_id, Film.title, Film.release_year)
            .limit(limit)
        )
        films = result.all()

        return str([
            {
                "film_id": f.film_id,
                "title": f.title,
                "year": f.release_year
            } for f in films
        ])

@mcp.tool
async def get_categories() -> str:
    """Lista categorías"""
    async with get_db_context() as session:
        result = await session.execute(
            select(Category.category_id, Category.name)
        )

        categories = result.all()

        return str([
            {
                "category_id": c.category_id,
                "name": c.name
            } for c in categories
        ])

@mcp.tool
async def get_most_rented_films(limit: int = 10) -> str:
    """Películas más alquiladas"""
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Film.title,
                func.count(Rental.rental_id).label("times_rented")
            )
            .join(Inventory, Inventory.film_id == Film.film_id)
            .join(Rental, Rental.inventory_id == Inventory.inventory_id)
            .group_by(Film.title)
            .order_by(func.count(Rental.rental_id).desc())
            .limit(limit)
        )

        films = result.all()
        return str([
            {
                "title": f.title,
                "times_rented": f.times_rented
            } for f in films
        ])

@mcp.tool(description="Devuelve los clientes que más alquileres han realizado")
async def get_top_customers(limit: int = 10) -> str:
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Customer.customer_id,
                Customer.first_name,
                Customer.last_name,
                func.count(Rental.rental_id).label("total_rentals")
            )
            .join(Rental, Rental.customer_id == Customer.customer_id)
            .group_by(
                Customer.customer_id,
                Customer.first_name,
                Customer.last_name
            )
            .order_by(func.count(Rental.rental_id).desc())
            .limit(limit)
        )

        rows = result.all()
        return str([
            {
                "customer_id": r.customer_id,
                "name": f"{r.first_name} {r.last_name}",
                "total_rentals": r.total_rentals
            }
            for r in rows
        ])

@mcp.tool
async def get_actor_films(actor_id: int = None, limit: int = 20) -> str:
    """
    Obtiene las películas de un actor específico o de varios actores.
    Si no se proporciona actor_id, lista películas de los primeros actores.
    """
    async with get_db_context() as session:
        query = (
            select(
                Actor.actor_id,
                Actor.first_name,
                Actor.last_name,
                Film.film_id,
                Film.title,
                Film.release_year
            )
            .join(FilmActor, FilmActor.actor_id == Actor.actor_id)
            .join(Film, Film.film_id == FilmActor.film_id)
        )
        
        if actor_id:
            query = query.where(Actor.actor_id == actor_id)
        else:
            # Si no se especifica, toma los primeros actores
            query = query.where(Actor.actor_id <= limit)
        
        query = query.order_by(Actor.actor_id, Film.title)
        
        result = await session.execute(query)
        films = result.all()
        
        # Agrupar por actor
        actors_dict = {}
        for row in films:
            actor_key = row.actor_id
            if actor_key not in actors_dict:
                actors_dict[actor_key] = {
                    "actor_id": row.actor_id,
                    "actor_name": f"{row.first_name} {row.last_name}",
                    "films": []
                }
            
            actors_dict[actor_key]["films"].append({
                "film_id": row.film_id,
                "title": row.title,
                "year": row.release_year
            })
        
        return str(list(actors_dict.values()))

@mcp.tool
async def get_actor_film_count(limit: int = 15) -> str:
    """
    Cuenta cuántas películas tiene cada actor
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Actor.actor_id,
                Actor.first_name,
                Actor.last_name,
                func.count(FilmActor.film_id).label("total_films")
            )
            .join(FilmActor, FilmActor.actor_id == Actor.actor_id)
            .group_by(Actor.actor_id, Actor.first_name, Actor.last_name)
            .order_by(func.count(FilmActor.film_id).desc())
            .limit(limit)
        )
        
        actors = result.all()
        
        return str([
            {
                "actor_id": a.actor_id,
                "name": f"{a.first_name} {a.last_name}",
                "total_films": a.total_films
            } for a in actors
        ])
    


@mcp.tool
async def get_top_categories_by_revenue(limit: int = 10) -> str:
    """Categorías con mayores ingresos"""
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Category.name,
                func.sum(Payment.amount).label("revenue")
            )
            .join(FilmCategory, FilmCategory.category_id == Category.category_id)
            .join(Film, Film.film_id == FilmCategory.film_id)
            .join(Inventory, Inventory.film_id == Film.film_id)
            .join(Rental, Rental.inventory_id == Inventory.inventory_id)
            .join(Payment, Payment.rental_id == Rental.rental_id)
            .group_by(Category.name)
            .order_by(func.sum(Payment.amount).desc())
            .limit(limit)
        )

        rows = result.all()
        return str([
            {"category": r.name, "revenue": float(r.revenue)}
            for r in rows
        ])


@mcp.tool
async def list_tables() -> str:
    """Lista las tablas disponibles en la base de datos"""
    async with get_db_context() as session:
        result = await session.execute(
            text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """)
        )
        return str(result.scalars().all())


@mcp.tool
async def list_columns(table_name: str) -> str:
    """Lista las columnas de una tabla"""
    async with get_db_context() as session:
        result = await session.execute(
            text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = :table
            """),
            {"table": table_name}
        )
        return str([
            {"column": row.column_name, "type": row.data_type}
            for row in result
        ])
