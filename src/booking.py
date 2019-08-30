import dotenv
dotenv.load_dotenv()

from datetime import datetime, date
import argparse
import logging
import os
from typing import Union

import requests
import shapely
from pyproj import Transformer
from flatdict import FlatDict
import pandas as pd

DT_FORMAT = "%Y-%m-%d"


def get_cheapest_nearby_hotels(loc: Union[str, tuple], t_arrival: date, t_departure: date, box_edge:int=20000):

    booking_session = requests.Session()
    booking_session.headers.update( {
        'x-rapidapi-host': "apidojo-booking-v1.p.rapidapi.com",
        'x-rapidapi-key': os.environ["RAPIDAPI_BOOKING_COM_API_KEY"]
    })

    epsg_gps = 4326
    epsg_utm32 = 32632

    transformer_gps_to_utm = Transformer.from_crs(epsg_gps, epsg_utm32)
    transformer_utm_to_gps = Transformer.from_crs(epsg_utm32, epsg_gps)

    loc_x, loc_y = transformer_gps_to_utm.transform(*loc)

    a = box_edge

    # north east
    loc_ne_x = loc_x + a/2
    loc_ne_y = loc_y + a/2

    # south west
    loc_sw_x = loc_x - a/2
    loc_sw_y = loc_y - a/2

    loc_ne_lat, loc_ne_lng = transformer_utm_to_gps.transform(loc_ne_x, loc_ne_y)
    loc_sw_lat, loc_sw_lng = transformer_utm_to_gps.transform(loc_sw_x, loc_sw_y)

    bbox_string = f"{loc_sw_lat},{loc_ne_lat},{loc_sw_lng},{loc_ne_lng}"

    querystring = {"search_id":"none",
               "price_filter_currencycode":"EUR",
               "languagecode":"de",
               "travel_purpose":"leisure",
               "categories_filter":"price::0-60,free_cancellation::1,class::1,class::0,class::2",
               "children_qty":"0",
               "order_by":"price",
               "guest_qty":"1",
               "room_qty":"1",
               "departure_date": t_departure.strftime(DT_FORMAT),
               "bbox": bbox_string,
               "arrival_date": t_arrival.strftime(DT_FORMAT)}

    map_url = "https://apidojo-booking-v1.p.rapidapi.com/properties/list-by-map"
    r = booking_session.get(map_url, params=querystring)

    r_json = r.json()
    r_results = r_json["result"]

    logging.info("Found {:d} results in the requested bounding box!")

    dict_list = [FlatDict(r ,delimiter=".") for r in r_results]

    df_hotels = pd.DataFrame(dict_list)

    return df_hotels
