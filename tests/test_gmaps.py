import unittest
from datetime import datetime, timedelta
import sys

from dotenv import load_dotenv
load_dotenv()

sys.path.append(".")
from src.gmaps import get_distances, get_locatation_attributes

class TestGmapsUtils(unittest.TestCase):

    def test_get_distances(self):

        loc_base = (49.146468, 9.221350)
        loc_dest1 = (49.080050, 9.308849)
        loc_dest2 = (49.40768, 8.69079)
        loc_dest3 = (52.531677, 13.381777) # Berlin

        destinations = [loc_dest1, loc_dest2, loc_dest3]

        t_departure = datetime.now() + timedelta(seconds=3600)

        df = get_distances(loc_base, destinations, t_departure)

        self.assertEqual(len(df), len(destinations))
        self.assertGreater(df.iloc[2]["distance.value"], df.iloc[0]["distance.value"])

    def test_geocoding(self):
        res = get_locatation_attributes('Flandernstraße Hochschule Esslingen')

        self.assertTrue(res["geometry"]["location"]["lat"])
        self.assertTrue(res["geometry"]["location"]["lng"])
