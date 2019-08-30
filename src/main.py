import dotenv
dotenv.load_dotenv()

from datetime import datetime, date
import argparse
import logging
import os, sys
from typing import Union

import pytz 
from jinja2 import Environment, FileSystemLoader
import requests
import shapely
from pyproj import Transformer
from flatdict import FlatDict
import pandas as pd

sys.path.append(".")
from src.gmaps import get_locatation_attributes, get_distances
from src.booking import get_cheapest_nearby_hotels
from src.utils import haversine


DT_FORMAT = "%Y-%m-%d"


def generate_report(df, outpath):

    file_loader = FileSystemLoader("./templates")
    env = Environment(loader=file_loader)

    template = env.get_template("final.html")

    dt_generated = datetime.now(tz=pytz.timezone('Europe/Berlin')).replace(microsecond=0).isoformat(sep=" ",)

    report_title = "Hotel search results for {:%d.%m.%Y} to {:%d.%m.%Y}".format(
        dt_query_arrival, dt_query_departure)
    fuel_price_str = "{:.2f}".format(1.51)

    render_args = {"title": report_title,
                "dt_generated": dt_generated,
                "fuel_price": fuel_price_str}
    output = template.render(**render_args)

    with open(outpath, "w") as f:
        f.write(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='uni-unterkunft')

    parser.add_argument("destination", type=str, default="Stuttgart", help="uni location")
    parser.add_argument("date_arrival", type=str, default="Stuttgart", help="day of arrival in %s format" % DT_FORMAT)
    parser.add_argument("date_departure", type=str, default="Stuttgart", help="day of departure in %s format" % DT_FORMAT)
    parser.add_argument("--box_edge", type=int, help="bounding box edge length in meters", default=25000)
    
    args = parser.parse_args()

    dest = args.destination
    date_arrival = datetime.strptime(args.date_arrival, DT_FORMAT)
    date_departure = datetime.strptime(args.date_departure, DT_FORMAT)
    box_edge = args.box_edge

    dest_info = get_locatation_attributes(dest)
    dest_loc = dest_info["geometry"]["location"]
    dest_loc = (dest_loc["lat"], dest_loc["lng"])

    dt_departure = datetime(date_departure.year, date_departure.month, date_departure.day, 21, 0, 0)
    df_hotels = get_cheapest_nearby_hotels(loc=dest_loc, t_arrival=date_arrival, t_departure=dt_departure)

    destinations = [(r["latitude"], r["longitude"]) for _, r in df_hotels.iterrows()]

    df_distances = get_distances(origin=dest_loc, destinations=destinations, departure_time=date_departure)

    df_final = df_hotels.join(df_distances)
    df_final["haversine_distance"] = df_final[["latitude", "longitude"]].apply(lambda row: haversine(row["latitude"], row["longitude"], dest_loc[0], dest_loc[1]), axis=1)

    df_final.to_csv("final.csv", index=False)
    df_final.to_excel("final.xlsx")
