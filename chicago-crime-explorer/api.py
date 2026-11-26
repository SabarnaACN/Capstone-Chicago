"""Validated CRUD endpoints and automatically generated OpenAPI documentation."""

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from schemas import (
    CommunityCreate, CommunityInput, CommunityListQuery, CommunityOutput, CommunityPage,
    CommunityPatch, CrimeInput, CrimeListQuery, CrimeOutput, CrimePage, CrimePatch, FilterQuery,
)
from use_case_4 import load_selection, summary_json
from database import RecordError, delete_record, find_record, reflect_tables, save_record

api = Blueprint("records", __name__, url_prefix="/api", description="Crime and community management")


def storage():
    if not current_app.config["DB_PATH"].is_file():
        abort(503, message="Run python use_case_1.py to create the database.")
    engine = current_app.extensions["engine"]
    if not current_app.extensions["tables"]:
        current_app.extensions["tables"] = reflect_tables(engine)
    return engine, current_app.extensions["tables"]


def handle_error(error):
    if isinstance(error, RecordError):
        abort(error.status, message=error.message, errors=error.errors or {})
    abort(409, message="A unique key already exists or a referenced record cannot be removed.")


def change(resource, data=None, identifier=None, remove=False):
    engine, tables = storage()
    try:
        with engine.begin() as connection:
            if remove:
                delete_record(connection, tables, resource, identifier)
                return None
            return save_record(connection, tables, resource, data, identifier)
    except (RecordError, IntegrityError) as error:
        handle_error(error)


def get_item(resource, identifier):
    engine, tables = storage()
    try:
        with engine.connect() as connection:
            return find_record(connection, tables, resource, identifier)
    except RecordError as error:
        handle_error(error)


def list_conditions(table, resource, args):
    conditions = []
    if resource == "crimes":
        for key, column in [("year", "year"), ("category", "primary_type"), ("community_code", "community_code")]:
            if key in args:
                conditions.append(table.c[column] == args[key])
        if "arrest" in args:
            flag = {"yes": 1, "no": 0, "unknown": None}[args["arrest"]]
            conditions.append(table.c.arrest == flag)
    elif "min_population" in args:
        conditions.append(table.c.population >= args["min_population"])

    if args["search"]:
        columns = ["case_number", "block", "community_name"] if resource == "crimes" else ["community_name"]
        conditions.append(or_(*(table.c[column].ilike(f"%{args['search']}%") for column in columns)))
    return conditions


def list_items(resource, args):
    engine, tables = storage()
    table = tables["vw_crime_enriched" if resource == "crimes" else "city_community"]
    conditions = list_conditions(table, resource, args)
    column_name, direction = args["sort"].rsplit("_", 1)
    column = table.c[column_name]
    if column_name in {"case_number", "primary_type", "community_name"}:
        column = column.collate("NOCASE")
    order = column.desc() if direction == "desc" else column.asc()
    tie_breaker = table.c.id.desc() if resource == "crimes" else table.c.community_code
    page, page_size = args["page"], args["page_size"]

    count_query = select(func.count()).select_from(table).where(*conditions)
    page_query = (
        select(table)
        .where(*conditions)
        .order_by(order, tie_breaker)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if resource == "communities":
        crimes = tables["chicago_crime"]
        count = select(func.count()).where(crimes.c.community_code == table.c.community_code).scalar_subquery()
        page_query = page_query.add_columns(count.label("crime_count"))
    with engine.connect() as connection:
        total = connection.execute(count_query).scalar_one()
        items = [dict(row) for row in connection.execute(page_query).mappings()]
    if resource == "communities":
        for area in items:
            population = area["population"]
            area["per_10000"] = 10000 * area["crime_count"] / population if population and population > 0 else None
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def register_crud(resource, query, create, replace, patch_schema, output, page):
    @api.route(f"/{resource}", endpoint=resource)
    class Collection(MethodView):
        @api.arguments(query, location="query")
        @api.response(200, page)
        def get(self, args):
            return list_items(resource, args)

        @api.arguments(create)
        @api.response(201, output)
        def post(self, data):
            return change(resource, data)

    @api.route(f"/{resource}/<int:identifier>", endpoint=f"{resource}_record")
    class Record(MethodView):
        @api.response(200, output)
        def get(self, identifier):
            return get_item(resource, identifier)

        @api.arguments(replace)
        @api.response(200, output)
        def put(self, data, identifier):
            return change(resource, data, identifier)

        @api.arguments(patch_schema(partial=True))
        @api.response(200, output)
        def patch(self, data, identifier):
            if not data:
                abort(422, message="Provide at least one editable field.")
            return change(resource, data, identifier)

        @api.response(204)
        def delete(self, identifier):
            return change(resource, identifier=identifier, remove=True)


register_crud("crimes", CrimeListQuery, CrimeInput, CrimeInput, CrimePatch, CrimeOutput, CrimePage)
register_crud(
    "communities", CommunityListQuery, CommunityCreate, CommunityInput,
    CommunityPatch, CommunityOutput, CommunityPage,
)


@api.route("/options")
@api.response(200)
def options():
    """Read dropdown choices from the database, including newly created records."""
    return lookup_options()


def lookup_options(*, include_form_details=True):
    engine, _ = storage()
    fields = "community_code, community_name"
    if include_form_details:
        fields += ", population"
    queries = {
        "communities": f"SELECT {fields} FROM city_community ORDER BY community_name",
    }
    if include_form_details:
        queries.update({
            "offences": "SELECT iucr_code, primary_type, description FROM iucr ORDER BY primary_type, iucr_code",
            "districts": "SELECT district_code, district_name FROM district_ps_info",
            "wards": "SELECT ward_no FROM ward_office",
            "beats": "SELECT beat_num FROM police_beat_info",
        })
    with engine.connect() as connection:
        options = {}
        for name, query in queries.items():
            rows = connection.exec_driver_sql(query).mappings()
            options[name] = [dict(row) for row in rows]
        options["years"] = list(connection.exec_driver_sql("SELECT DISTINCT year FROM chicago_crime ORDER BY year").scalars())
        options["categories"] = list(connection.exec_driver_sql("SELECT DISTINCT primary_type FROM iucr ORDER BY primary_type").scalars())
        if include_form_details:
            options["latest_date"] = connection.exec_driver_sql("SELECT MAX(date) FROM chicago_crime").scalar()
    return options


@api.route("/analytics")
@api.arguments(FilterQuery, location="query")
@api.response(200)
def analytics(args):
    storage()
    selection = load_selection(current_app.config["DB_PATH"], args)
    result = summary_json(selection.stats, selection.filters, selection.quality)
    result.update(full_total=selection.full_total, quality=selection.quality)
    return result
