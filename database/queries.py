def build_filter_query(filters: dict) -> tuple[str, list]:
    clauses = []
    params = []

    for key, value in filters.items():
        if value is None or value == "":
            continue

        if key.endswith("_min"):
            field = key[:-4]
            clauses.append(f"{field} >= ?")
            params.append(value)
        elif key.endswith("_max"):
            field = key[:-4]
            clauses.append(f"{field} <= ?")
            params.append(value)
        elif key in (
            "has_elevator", "has_parking", "has_balcony", "has_ac",
            "is_furnished", "pets_allowed", "has_mamad", "has_bars",
        ):
            if value is True or value == "true" or value == "1":
                clauses.append(f"{key} = 1")
        elif key in ("city", "address_full"):
            clauses.append(f"{key} LIKE ?")
            params.append(f"%{value}%")

    where = " AND ".join(clauses) if clauses else "1=1"
    return where, params
