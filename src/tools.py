#Aquí se define las herramientas MCP que Claude puede usar para 
#consultar la base de datos de forma segura.
import logging
from fastmcp import FastMCP
from sqlalchemy import select, func, text

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


# MCP SERVER

mcp = FastMCP("Pagila MCP Server")


# RESPUESTA ESTRUCTURADA 

def visual_report(
    title: str,
    description: str,
    columns: list[str],
    rows: list[list],
    summary: str | None = None,
    format_columns: dict | None = None
):
    """
    Devuelve:
    - data: JSON estructurado (Claude-friendly)
    - markdown: tabla visual + resumen
    """

    structured_rows = []
    for row in rows:
        obj = {}
        for i, col in enumerate(columns):
            value = row[i]
            if format_columns and i in format_columns:
                if format_columns[i] == "currency":
                    value = round(float(value), 2)
                elif format_columns[i] == "number":
                    value = int(value)
            obj[col] = value
        structured_rows.append(obj)

    # Markdown visual
    md = f"## {title}\n\n*{description}*\n\n"
    md += "| " + " | ".join(columns) + " |\n"
    md += "| " + " | ".join(["---"] * len(columns)) + " |\n"

    for r in structured_rows:
        md += "| " + " | ".join(str(r[c]) for c in columns) + " |\n"

    if summary:
        md += f"\n###  Análisis\n{summary}\n"

    return {
        "title": title,
        "description": description,
        "columns": columns,
        "data": structured_rows,
        "markdown": md
    }

# =========================
# EXPLORACIÓN DE BD
# =========================

@mcp.tool
async def list_tables():
    async with get_db_context() as session:
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))

        rows = [[t] for t in result.scalars().all()]

        return visual_report(
            "Tablas disponibles",
            "Tablas públicas de la base de datos Pagila.",
            ["tabla"],
            rows
        )


@mcp.tool
async def list_columns(table_name: str):
    async with get_db_context() as session:
        result = await session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = :table
            ORDER BY ordinal_position
        """), {"table": table_name})

        rows = [[r.column_name, r.data_type] for r in result]

        return visual_report(
            f"Estructura de {table_name}",
            "Columnas y tipos de datos.",
            ["columna", "tipo"],
            rows
        )


# CONSULTAS DE NEGOCIO (DINÁMICAS)


@mcp.tool
async def top_customers_by_rentals(top_n: int = 10):
    """
    Top N clientes según número de alquileres.
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Customer.customer_id,
                func.concat(Customer.first_name, " ", Customer.last_name).label("cliente"),
                func.count(Rental.rental_id).label("alquileres")
            )
            .join(Rental)
            .group_by(Customer.customer_id)
            .order_by(func.count(Rental.rental_id).desc())
            .limit(top_n)
        )

        rows = [
            [r.customer_id, r.cliente, r.alquileres]
            for r in result.all()
        ]

        return visual_report(
            title=f"Top {top_n} clientes por alquileres",
            description="Ranking dinámico de clientes más activos.",
            columns=["customer_id", "cliente", "alquileres"],
            rows=rows,
            summary="Los clientes en las primeras posiciones representan el mayor volumen de actividad.",
            format_columns={2: "number"}
        )


@mcp.tool
async def top_customers_by_revenue(top_n: int = 10):
    """
    Top N clientes según ingresos generados.
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Customer.customer_id,
                func.concat(Customer.first_name, " ", Customer.last_name).label("cliente"),
                func.sum(Payment.amount).label("ingresos")
            )
            .join(Payment)
            .group_by(Customer.customer_id)
            .order_by(func.sum(Payment.amount).desc())
            .limit(top_n)
        )

        rows = [
            [r.customer_id, r.cliente, r.ingresos]
            for r in result.all()
        ]

        return visual_report(
            title=f"Top {top_n} clientes por ingresos",
            description="Clientes que más dinero han generado.",
            columns=["customer_id", "cliente", "ingresos"],
            rows=rows,
            summary="Este ranking identifica a los clientes más rentables para el negocio.",
            format_columns={2: "currency"}
        )


@mcp.tool
async def top_categories_by_revenue(top_n: int = 10):
    """
    Categorías más rentables (dinámico).
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Category.name.label("categoria"),
                func.sum(Payment.amount).label("ingresos")
            )
            .join(FilmCategory)
            .join(Film)
            .join(Inventory)
            .join(Rental)
            .join(Payment)
            .group_by(Category.name)
            .order_by(func.sum(Payment.amount).desc())
            .limit(top_n)
        )

        rows = [
            [r.categoria, r.ingresos]
            for r in result.all()
        ]

        return visual_report(
            title=f"Top {top_n} categorías más rentables",
            description="Ranking de categorías según ingresos totales.",
            columns=["categoría", "ingresos"],
            rows=rows,
            summary=(
                "Las primeras categorías concentran la mayor parte de los ingresos, "
                "lo que permite priorizar inversión y marketing."
            ),
            format_columns={1: "currency"}
        )



FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "truncate"]

@mcp.tool
async def run_safe_query(sql: str, limit: int = 100):
    """
    Ejecuta SELECT seguro con límite automático.
    """
    lowered = sql.lower()

    if not lowered.startswith("select"):
        return " Solo se permiten consultas SELECT."

    if any(word in lowered for word in FORBIDDEN):
        return " Consulta bloqueada por seguridad."

    if "limit" not in lowered:
        sql += f" LIMIT {limit}"

    async with get_db_context() as session:
        result = await session.execute(text(sql))
        rows = result.fetchall()

        if not rows:
            return "Consulta ejecutada sin resultados."

        return visual_report(
            title="Resultado de consulta SQL",
            description="Consulta ejecutada de forma segura.",
            columns=list(result.keys()),
            rows=[list(r) for r in rows]
        )

@mcp.tool
async def top_actors_by_film_count(top_n: int = 10):
    """
    Top N actores según cantidad de películas en las que participan.
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Actor.actor_id,
                func.concat(Actor.first_name, " ", Actor.last_name).label("actor"),
                func.count(FilmActor.film_id).label("peliculas")
            )
            .join(FilmActor)
            .group_by(Actor.actor_id)
            .order_by(func.count(FilmActor.film_id).desc())
            .limit(top_n)
        )

        rows = [
            [r.actor_id, r.actor, r.peliculas]
            for r in result.all()
        ]

        return visual_report(
            title=f"Top {top_n} actores con más películas",
            description="Ranking dinámico de actores según número de películas.",
            columns=["actor_id", "actor", "películas"],
            rows=rows,
            summary=(
                "Los actores en las primeras posiciones tienen mayor presencia en el catálogo, "
                "lo que puede indicar alta demanda o popularidad."
            ),
            format_columns={2: "number"}
        )
@mcp.tool
async def top_actors_by_revenue(top_n: int = 10):
    """
    Top N actores según ingresos generados por sus películas.
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Actor.actor_id,
                func.concat(Actor.first_name, " ", Actor.last_name).label("actor"),
                func.sum(Payment.amount).label("ingresos")
            )
            .join(FilmActor)
            .join(Film)
            .join(Inventory)
            .join(Rental)
            .join(Payment)
            .group_by(Actor.actor_id)
            .order_by(func.sum(Payment.amount).desc())
            .limit(top_n)
        )

        rows = [
            [r.actor_id, r.actor, r.ingresos]
            for r in result.all()
        ]

        return visual_report(
            title=f"Top {top_n} actores más rentables",
            description="Actores ordenados por ingresos totales generados.",
            columns=["actor_id", "actor", "ingresos"],
            rows=rows,
            summary=(
                "Este ranking permite identificar a los actores con mayor impacto económico "
                "dentro del catálogo."
            ),
            format_columns={2: "currency"}
        )
@mcp.tool
async def films_by_actor(actor_name: str):
    """
    Devuelve SIEMPRE una tabla visual con las películas de un actor.
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Film.title,
                Category.name.label("categoria"),
                Film.release_year
            )
            .join(FilmActor)
            .join(Actor)
            .join(FilmCategory)
            .join(Category)
            .where(
                func.lower(
                    func.concat(Actor.first_name, " ", Actor.last_name)
                ).like(f"%{actor_name.lower()}%")
            )
            .order_by(Film.title)
        )

        films = result.all()
        total = len(films)

        rows = [[f.title, f.categoria, f.release_year] for f in films]

        return {
            "title": f"Películas del actor: {actor_name}",
            "total_peliculas": total,
            "markdown": (
                f"##  Películas de {actor_name}\n\n"
                f"**Total de películas:** {total}\n\n"
                "| Película | Categoría | Año |\n"
                "|----------|-----------|-----|\n"
                + "\n".join(
                    f"| {f[0]} | {f[1]} | {f[2]} |"
                    for f in rows
                )
            ),
            "data": rows
        }
@mcp.tool
async def top_rented_movies(top_n: int = 10):
    """
    Ranking dinámico de las películas más alquiladas.
    """
    async with get_db_context() as session:
        result = await session.execute(
            select(
                Film.title,
                func.count(Rental.rental_id).label("total")
            )
            .join(Inventory, Inventory.film_id == Film.film_id)
            .join(Rental, Rental.inventory_id == Inventory.inventory_id)
            .group_by(Film.title)
            .order_by(func.count(Rental.rental_id).desc())
            .limit(top_n)
        )

        rows = result.all()

        return {
            "title": f"Top {top_n} películas más alquiladas",
            "total_peliculas": len(rows),
            "markdown": (
                f"##  Top {top_n} películas más alquiladas\n\n"
                "| Posición | Película | Total de alquileres |\n"
                "|----------|----------|---------------------|\n"
                + "\n".join(
                    f"| {i+1} | {r.title} | {r.total} |"
                    for i, r in enumerate(rows)
                )
            ),
            "data": [
                {
                    "posicion": i + 1,
                    "pelicula": r.title,
                    "alquileres": r.total
                }
                for i, r in enumerate(rows)
            ]
        }
@mcp.tool
async def top_profitable_categories(top_n: int = 10):
    """
    Ranking dinámico de las categorías con mayores ingresos.
    """
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
            .limit(top_n)
        )

        rows = result.all()

        return {
            "title": f"Top {top_n} categorías más rentables",
            "markdown": (
                f"## Categorías más rentables\n\n"
                "| Posición | Categoría | Ingresos |\n"
                "|----------|-----------|----------|\n"
                + "\n".join(
                    f"| {i+1} | {r.name} | ${r.revenue:,.2f} |"
                    for i, r in enumerate(rows)
                )
            ),
            "data": [
                {
                    "posicion": i + 1,
                    "categoria": r.name,
                    "ingresos": float(r.revenue)
                }
                for i, r in enumerate(rows)
            ]
        }
