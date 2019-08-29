from datetime import datetime, date
import pytz 
from jinja2 import Environment, FileSystemLoader

file_loader = FileSystemLoader("./templates")
env = Environment(loader=file_loader)

template = env.get_template("final.html")

dt_generated = datetime.now(tz=pytz.timezone('Europe/Berlin')).replace(microsecond=0).isoformat(sep=" ",)

# TODO find next weekend if possible
dt_query_arrival = date(2019, 9, 13)
dt_query_departure = date(2019, 9, 14)

report_title = "Hotel search results for {:%d.%m.%Y} to {:%d.%m.%Y}".format(
    dt_query_arrival, dt_query_departure)
fuel_price_str = "{:.2f}".format(1.51)

render_args = {"title": report_title,
               "dt_generated": dt_generated,
               "fuel_price": fuel_price_str}
output = template.render(**render_args)

with open("examples/final.html", "w") as f:
    f.write(output)

