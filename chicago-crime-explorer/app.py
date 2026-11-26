"""Flask pages, HTML forms and exports."""

import json
import secrets
from pathlib import Path

from flask import (
    Flask, Response, flash, redirect, render_template, request, send_file, session, url_for,
)
from flask_smorest import Api, abort
from flask_swagger_ui import get_swaggerui_blueprint
from marshmallow import EXCLUDE, ValidationError, fields
from werkzeug.exceptions import HTTPException

from use_case_4 import CHARTS, chart_png, load_selection, make_report, summary_json
from schemas import (
    CommunityCreate, CommunityInput, CommunityListQuery,
    CrimeInput, CrimeListQuery, DashboardQuery, FilterQuery,
)
from api import api as records_api, change, get_item, list_items, lookup_options
from database import DB_PATH, create_db_engine


def parse_filters(schema):
    values = {key: value.strip() for key, value in request.args.items() if value.strip()}
    return schema.load(values, unknown=EXCLUDE)


def form_values(schema):
    values = request.form.to_dict()
    values.pop("csrf_token", None)
    for name, field in schema.fields.items():
        value = values.get(name)
        if value == "" and field.allow_none:
            values[name] = None
        elif isinstance(field, fields.Integer) and value is not None:
            try:
                values[name] = int(value)
            except ValueError:
                pass
    return values


def edited_fields(changes, record):
    date = changes.get("date")
    if date and date.isoformat() == str(record["date"])[:10]:
        changes.pop("date")
    return {field: value for field, value in changes.items() if value != record.get(field)}


def list_schema(resource):
    return CrimeListQuery() if resource == "crimes" else CommunityListQuery()


def list_query(resource):
    """Keep only known list parameters when linking back from a form."""
    allowed = list_schema(resource).fields
    return {key: value for key, value in request.args.items() if key in allowed and value}


def create_app(db_path=DB_PATH, testing=False):
    app = Flask(__name__)
    app.config.update(
        TESTING=testing,
        DB_PATH=Path(db_path),
        SECRET_KEY=secrets.token_hex(32),
        API_TITLE="Chicago Crime Explorer API",
        API_VERSION="1.0",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/api",
        OPENAPI_JSON_PATH="openapi.json",
        SESSION_COOKIE_SAMESITE="Lax",
    )
    app.extensions["engine"] = create_db_engine(db_path)
    app.extensions["tables"] = {}
    api = Api(app)
    app.register_blueprint(get_swaggerui_blueprint(
        "/api/docs", "/api/openapi.json",
        config={"app_name": "Chicago Crime Explorer", "validatorUrl": None},
    ))

    def selection(args):
        if not app.config["DB_PATH"].is_file():
            abort(503, message="Run python use_case_1.py to create the database.")
        return load_selection(app.config["DB_PATH"], args)

    @app.before_request
    def verify_form():
        if request.method == "POST" and request.endpoint == "record_form":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token", "")
            if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
                abort(400, message="The form has expired. Open it again and retry.")

    @app.template_global()
    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        return session["csrf_token"]

    @app.template_filter("number")
    def number(value, decimals=0):
        return "—" if value is None or value != value else f"{value:,.{decimals}f}"

    @app.get("/")
    def index():
        choices = parse_filters(DashboardQuery())
        filter_names = FilterQuery().fields
        filters = {name: choices[name] for name in filter_names if name in choices}
        results = selection(filters)
        stats = results.stats
        category_limit = 5 if choices["ranking"] == "top5" else 10

        return render_template(
            "dashboard.html",
            options=lookup_options(include_form_details=False),
            filters=filters,
            choices=choices,
            stats=stats,
            full_total=results.full_total,
            dashboard_filters=filters,
            yearly=stats["yearly"].to_dict("records"),
            categories=stats["categories"].head(category_limit).to_dict("records"),
            community=stats["communities"].head(1).to_dict("records"),
        )

    @app.get("/<any(crimes,communities):resource>")
    def records(resource):
        filters = parse_filters(list_schema(resource))
        result = list_items(resource, filters)
        last_page = max(1, (result["total"] + result["page_size"] - 1) // result["page_size"])
        query = list_query(resource)
        if filters["page"] > last_page:
            return redirect(url_for("records", resource=resource, **(query | {"page": last_page})))
        dashboard_filters = parse_filters(FilterQuery()) if resource == "crimes" else {}
        page_query = {key: value for key, value in query.items() if key != "page"}
        return render_template(
            "records.html",
            resource=resource,
            filters=filters,
            result=result,
            last_page=last_page,
            options=lookup_options(include_form_details=False) if resource == "crimes" else {},
            query=query,
            dashboard_filters=dashboard_filters,
            page_query=page_query,
        )

    @app.route("/<any(crimes,communities):resource>/new", methods=["GET", "POST"], defaults={"deleting": False})
    @app.route("/<any(crimes,communities):resource>/<int:identifier>/edit", methods=["GET", "POST"], defaults={"deleting": False})
    @app.route(
        "/<any(crimes,communities):resource>/<int:identifier>/delete",
        methods=["GET", "POST"], defaults={"deleting": True},
    )
    def record_form(resource, identifier=None, deleting=False):
        query = list_query(resource)
        record = get_item(resource, identifier) if identifier is not None else {}
        values, options = record.copy(), {}
        if resource == "crimes" and not deleting:
            options = lookup_options()
            values["date"] = str(record.get("date", ""))[:10]
            values.setdefault("community_code", query.get("community_code", ""))

        errors, message, status = {}, "", 200
        if request.method == "POST":
            try:
                if deleting:
                    change(resource, identifier=identifier, remove=True)
                    flash("Record deleted.")
                else:
                    if resource == "crimes":
                        schema = CrimeInput()
                    else:
                        schema = CommunityInput() if record else CommunityCreate()
                    submitted = form_values(schema)
                    values.update(submitted)
                    changes = schema.load(submitted)
                    if record:
                        changes = edited_fields(changes, record)
                    if changes:
                        change(resource, changes, identifier)
                    flash("Record saved." if changes else "No changes to save.")
                return redirect(url_for("records", resource=resource, **query), code=303)
            except ValidationError as error:
                errors, message, status = error.messages, "Check the fields listed below.", 422
            except HTTPException as error:
                details = getattr(error, "data", {})
                errors = details.get("errors", {})
                message, status = details.get("message", error.description), error.code

        return render_template(
            "record_form.html", resource=resource, record=record, values=values,
            options=options, errors=errors, message=message, query=query, deleting=deleting,
        ), status

    @app.get("/charts/<name>.png")
    def chart(name):
        if name not in CHARTS:
            abort(404, message="Unknown chart.")
        results = selection(parse_filters(FilterQuery()))
        return send_file(chart_png(name, results.incidents, results.stats), mimetype="image/png", max_age=0)

    @app.get("/export/<kind>")
    def export(kind):
        results = selection(parse_filters(FilterQuery()))
        if kind == "records.csv":
            data, mime = results.incidents.to_csv(index=False), "text/csv"
        elif kind == "summary.json":
            data = json.dumps(summary_json(results.stats, results.filters, results.quality), indent=2)
            mime = "application/json"
        elif kind == "report.html":
            data = make_report(results.stats, results.filters)
            mime = "text/html"
        else:
            abort(404, message="Unknown export.")
        return Response(data, mimetype=mime, headers={
            "Content-Disposition": f'attachment; filename="chicago-{kind}"'
        })

    @app.errorhandler(ValidationError)
    def invalid_filters(error):
        if request.path.startswith(("/charts/", "/export/")):
            return {"message": "Invalid filters.", "errors": error.messages}, 422
        return render_template("base.html", problem="Check the filter values and try again.",
                               error_fields=error.messages), 422

    @app.errorhandler(HTTPException)
    def page_error(error):
        if request.path.startswith(("/api/", "/charts/", "/export/")):
            return api.handle_http_exception(error)
        problem = getattr(error, "data", {}).get("message", error.description)
        return render_template("base.html", problem=problem), error.code

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    api.register_blueprint(records_api)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=5057)
