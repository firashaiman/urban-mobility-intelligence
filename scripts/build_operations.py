import argparse
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd


OUTPUT_COLUMNS = [
    "Route_id", "Transport_type", "Trip_id", "Arrival_time", "Departure_time",
    "Stop_id", "Stop_name", "Stop_lat", "Stop_lon", "Stop_search",
    "Next_Stop_Lat", "Next_Stop_Lon", "NextStopName", "Route_long_name",
    "Distance_km", "Dwell_Time_mins", "Travel_Time_Next_mins", "Average_Speed_kmh",
    "Service_Days", "Peak_Hour_Flag", "Time_of_Day",
]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
WEEKEND = ["saturday", "sunday"]
PRASARANA_MODES = {"LRT": "LRT", "MRT": "MRT", "MRL": "MONORAIL", "BRT": "BRT"}
FEED_TYPES = ("prasarana", "ktmb", "basmy")
TIME_BANDS = [
    "Early Morning", "Morning Peak", "Mid-Day Off-Peak",
    "Evening Peak", "Late Night Off-Peak",
]


def read_table(directory: Path, name: str, columns: list[str]) -> pd.DataFrame:
    path = directory / f"{name}.txt"
    table = pd.read_csv(path, dtype="string", usecols=columns)[columns]
    # Text IDs preserve leading zeros and avoid float conversion during file import.
    for field in columns:
        if field.endswith("_id"):
            table[field] = table[field].str.strip()
            if table[field].fillna("").eq("").any():
                raise ValueError(f"{path} contains missing values in {field}.")
    return table


def service_days(directory: Path, services: pd.Series) -> pd.Series:
    if not (directory / "calendar.txt").is_file():
        return pd.Series(pd.NA, index=services.index, dtype="string")

    calendar = read_table(directory, "calendar", ["service_id", *WEEKDAYS, *WEEKEND])
    if calendar["service_id"].duplicated().any():
        raise ValueError(f"{directory}/calendar.txt has duplicate service IDs.")

    # Inspect the entire week so a Friday-only service is still classed as a
    # weekday service. Mixed weekday/weekend services get their own label.
    # Date exceptions are outside these recurring weekly labels.
    weekdays = calendar[WEEKDAYS].eq("1").any(axis=1)
    weekend = calendar[WEEKEND].eq("1").any(axis=1)
    label = pd.Series(pd.NA, index=calendar.index, dtype="string")
    label.loc[weekdays & ~weekend] = "Weekday"
    label.loc[~weekdays & weekend] = "Weekend/Holiday"
    label.loc[weekdays & weekend] = "Weekday and Weekend"
    return services.map(dict(zip(calendar["service_id"], label))).astype("string")


def seconds_since_service_start(times: pd.Series) -> pd.Series:
    # GTFS hours can exceed 23. Keep those hours for duration calculations
    # so a trip crossing midnight stays in chronological order.
    parts = times.str.strip().str.extract(r"^(\d+):([0-5]\d):([0-5]\d)$").astype(float)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def straight_line_km(lat: float, lon: float, next_lat: float, next_lon: float) -> float:
    if any(pd.isna(value) for value in (lat, lon, next_lat, next_lon)):
        return float("nan")
    lat, lon, next_lat, next_lon = map(radians, (lat, lon, next_lat, next_lon))
    term = sin((next_lat - lat) / 2) ** 2 + cos(lat) * cos(next_lat) * sin(
        (next_lon - lon) / 2
    ) ** 2
    return 6371 * 2 * asin(sqrt(min(1, term)))


def build_feed(feed_type: str, directory: Path) -> pd.DataFrame:
    times = read_table(
        directory, "stop_times",
        ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"],
    )
    trips = read_table(directory, "trips", ["trip_id", "route_id", "service_id"])
    stops = read_table(directory, "stops", ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    route_columns = ["route_id", "route_long_name"]
    if feed_type == "prasarana":
        route_columns.append("category")
    routes = read_table(directory, "routes", route_columns)

    times["stop_sequence"] = pd.to_numeric(times["stop_sequence"], errors="raise").astype("Int64")
    if times["stop_sequence"].isna().any() or times.duplicated(["trip_id", "stop_sequence"]).any():
        raise ValueError(f"{directory}/stop_times.txt has missing or duplicate trip sequences.")

    # Join from stop times to the trip, route and stop lookup tables. The
    # many-to-one checks guard against duplicate lookup keys inflating the row count.
    records = times.merge(trips, on="trip_id", how="left", validate="many_to_one")
    records = records.merge(routes, on="route_id", how="left", validate="many_to_one")
    records = records.merge(stops, on="stop_id", how="left", validate="many_to_one")
