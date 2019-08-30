import os
from datetime import datetime

import googlemaps
from flatdict import FlatDict
import pandas as pd

gmaps = googlemaps.Client(key=os.environ["GMAPS_API_KEY"])


def get_distances(origin, destinations, departure_time:datetime):

    result_dict = gmaps.distance_matrix(origin, destinations,
                mode="driving", units="metric", 
                departure_time=departure_time)

    result_dict_flat = FlatDict(result_dict, delimiter=".")
    dict_list = [FlatDict(r, delimiter=".") for r in result_dict["rows"][0]["elements"]]
    df_distances = pd.DataFrame(dict_list)
    return df_distances


def get_locatation_attributes(location_string):
    result_dict = gmaps.geocode(location_string)[0]
    return result_dict
