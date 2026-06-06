import cudf

def compute_impact(
    affected_nodes: cudf.DataFrame,
    stops: cudf.DataFrame,
    demographics: cudf.DataFrame,
    businesses: cudf.DataFrame,
) -> dict:
    """
    Joins BFS-affected nodes against London datasets to compute human impact metrics.

    affected_nodes: cuDF with columns [node, distance]
    stops: cuDF with columns [stop_id, node_id, lsoa_code, daily_boardings]
    demographics: cuDF with columns [lsoa_code, population, imd_decile]
    businesses: cuDF with columns [borough, business_count] (borough-level proxy)

    Returns dict with: journeys_affected, population_impacted, avg_imd_decile, businesses_in_zone
    """
    # Join affected nodes → stops
    affected_stops = affected_nodes.merge(
        stops.rename(columns={"node_id": "node"}),
        on="node",
        how="inner"
    )
    journeys = int(affected_stops["daily_boardings"].sum()) if len(affected_stops) > 0 else 0

    # Join affected stops → demographics via LSOA
    if len(affected_stops) == 0:
        return {
            "journeys_affected": 0,
            "population_impacted": 0,
            "avg_imd_decile": 5,
            "businesses_in_zone": 0,
        }

    affected_lsoas = affected_stops[["lsoa_code"]].drop_duplicates()
    lsoa_data = affected_lsoas.merge(demographics, on="lsoa_code", how="left")
    lsoa_data["imd_decile"] = lsoa_data["imd_decile"].fillna(5)
    lsoa_data["population"] = lsoa_data["population"].fillna(1500)

    population = int(lsoa_data["population"].sum())

    total_pop = float(lsoa_data["population"].sum())
    if total_pop > 0:
        weighted_imd = float((lsoa_data["population"] * lsoa_data["imd_decile"]).sum()) / total_pop
    else:
        weighted_imd = 5.0

    # Business count: use total from businesses table as a proxy for now
    # (borough-level data — sum all as a conservative estimate)
    biz_total = int(businesses["business_count"].sum()) if len(businesses) > 0 else 0

    return {
        "journeys_affected": journeys,
        "population_impacted": population,
        "avg_imd_decile": round(weighted_imd, 2),
        "businesses_in_zone": biz_total,
    }
