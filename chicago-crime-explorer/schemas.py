from marshmallow import Schema, fields, post_dump, pre_load, validate


class CrimeInput(Schema):
    case_number = fields.Str(required=True, validate=validate.Length(min=1, max=32))
    date = fields.Date(required=True, metadata={"description": "Incident date: YYYY-MM-DD"})
    iucr_code = fields.Str(required=True, validate=validate.Regexp(r"^[0-9A-Z]{4}$"))
    community_code = fields.Int(required=True, strict=True, validate=validate.Range(min=1))
    block = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=120))
    location_desc = fields.Str(load_default="UNKNOWN", validate=validate.Length(min=1, max=120))
    arrest = fields.Bool(allow_none=True, load_default=None)
    domestic = fields.Bool(allow_none=True, load_default=None)
    district_code = fields.Int(allow_none=True, load_default=None, strict=True)
    ward_no = fields.Int(allow_none=True, load_default=None, strict=True)
    beat_num = fields.Int(allow_none=True, load_default=None, strict=True)
    latitude = fields.Float(allow_none=True, load_default=None, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(allow_none=True, load_default=None, validate=validate.Range(min=-180, max=180))

    @pre_load
    def normalize_text(self, data, **_):
        if not isinstance(data, dict):
            return data
        result = {
            key: value.strip().upper() if isinstance(value, str) else value
            for key, value in data.items()
        }
        if isinstance(result.get("iucr_code"), str):
            result["iucr_code"] = result["iucr_code"].zfill(4)
        return result


class CrimePatch(CrimeInput):
    """All input fields become optional for partial updates."""


class CrimeOutput(CrimeInput):
    id = fields.Int()
    date = fields.Str()
    primary_type = fields.Str(allow_none=True)
    community_name = fields.Str(allow_none=True)
    year = fields.Int()
    month = fields.Int()
    day_of_week = fields.Int()
    hour = fields.Int(allow_none=True)
    has_time = fields.Int()
    source_row = fields.Int(allow_none=True)
    date_of_update = fields.Str(allow_none=True)

    @post_dump
    def serialize_flags(self, record, **_):
        for name in ("arrest", "domestic"):
            if record.get(name) is not None:
                record[name] = bool(record[name])
        return record


class CommunityInput(Schema):
    community_name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    population = fields.Int(required=True, strict=True, validate=validate.Range(min=1))

    @pre_load
    def strip_name(self, data, **_):
        if isinstance(data, dict):
            data = dict(data)
            if isinstance(data.get("community_name"), str):
                data["community_name"] = data["community_name"].strip()
        return data


class CommunityPatch(CommunityInput):
    """Partial updates use the same validation rules."""


class CommunityCreate(CommunityInput):
    community_code = fields.Int(required=True, strict=True, validate=validate.Range(min=1))


class CommunityOutput(CommunityCreate):
    area_sqmile = fields.Float(allow_none=True)
    area_sqkm = fields.Float(allow_none=True)
    density_per_sqmi = fields.Float(allow_none=True)
    density_per_sqkm = fields.Float(allow_none=True)


class FilterQuery(Schema):
    year = fields.Int(validate=validate.Range(min=1))
    category = fields.Str(validate=validate.Length(max=120))
    community_code = fields.Int(validate=validate.Range(min=1))


class ListQuery(Schema):
    search = fields.Str(load_default="", validate=validate.Length(max=120))
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(load_default=25, validate=validate.Range(min=1, max=100))


class CrimeListQuery(ListQuery, FilterQuery):
    sort = fields.Str(load_default="id_desc", validate=validate.OneOf([
        "id_desc", "date_desc", "date_asc", "case_number_asc", "primary_type_asc",
    ]))
    arrest = fields.Str(validate=validate.OneOf(["yes", "no", "unknown"]))


class CommunityListQuery(ListQuery):
    sort = fields.Str(load_default="community_name_asc", validate=validate.OneOf([
        "community_name_asc", "community_name_desc", "population_desc",
        "population_asc", "community_code_asc",
    ]))
    min_population = fields.Int(validate=validate.Range(min=0, max=2**63 - 1))


class CrimePage(Schema):
    items = fields.List(fields.Nested(CrimeOutput))
    total = fields.Int()
    page = fields.Int()
    page_size = fields.Int()


class CommunityPage(Schema):
    items = fields.List(fields.Nested(CommunityOutput))
    total = fields.Int()
    page = fields.Int()
    page_size = fields.Int()


class DashboardQuery(FilterQuery):
    period = fields.Str(load_default="yearly", validate=validate.OneOf(["yearly", "monthly"]))
    ranking = fields.Str(load_default="categories", validate=validate.OneOf(["categories", "top5"]))
    arrests = fields.Str(load_default="arrests", validate=validate.OneOf(["arrests", "arrest-counts"]))
    areas = fields.Str(load_default="communities", validate=validate.OneOf(["communities", "normalized"]))
