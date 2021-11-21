import plotly_express as px
import numpy as np
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_bootstrap_components.themes import BOOTSTRAP
import dash_daq as daq
from math import cos, radians
import pandas as pd
import requests


# pd.set_option("display.max_columns", None)

base_url = "https://wxs.ign.fr/essentiels/geoportail/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature" \
	"&TYPENAME=BDTOPO_V3:batiment&SRSNAME=EPSG:4326&BBOX={min_lon},{min_lat},{max_lon},{max_lat},EPSG:4326" \
	"&STARTINDEX={offset}&MAXFEATURES=1000&outputFormat=application/json"


def lon_lat_offset(base_lat, size):
	offset_lat = size / 111_111
	offset_lon = size / (111_111 * cos(radians(base_lat)))
	return offset_lon, offset_lat


def fetch_data(center_lon, center_lat, size):
	offset_lon, offset_lat = lon_lat_offset(center_lat, size / 2)
	min_lon = center_lon - offset_lon
	min_lat = center_lat - offset_lat
	max_lon = center_lon + offset_lon
	max_lat = center_lat + offset_lat

	py_data = []
	json_data = {"type": "FeatureCollection", "features": []}

	offset = 0
	fetching = True
	while fetching:
		url = base_url.format(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat, offset=offset)
		print(f"Requesting URL: {url}")
		req = requests.get(url)
		res = req.json()

		for feature in res["features"]:
			json_data["features"].append(feature)
			properties = feature["properties"]
			py_data.append((
				feature["id"],
				feature["geometry"],
				properties["nature"],
				properties["usage_1"],
				properties["nombre_d_etages"],
				properties["hauteur"],
				properties["nombre_de_logements"]
			))

		offset += res["numberReturned"]
		fetching = offset < res["numberMatched"]

	columns = ["id", "geometry", "nature", "usage", "etages", "hauteur", "logements"]
	return json_data, pd.DataFrame(py_data, columns=columns)


if __name__ == "__main__":
	lon, lat = 2.523465, 48.784459
	# lon, lat = 2.294801, 48.858228
	data = {"dark": True, "lon": lon, "lat": lat, "size": 500}

	app = dash.Dash(__name__, external_stylesheets=[BOOTSTRAP])

	def content(reload_data):
		template = "plotly_dark" if data["dark"] else None
		if reload_data or "dataset" not in data or "geojson" not in data:
			geojson, dataset = fetch_data(data["lon"], data["lat"], data["size"])
			data["geojson"] = geojson
			data["dataset"] = dataset
		else:
			geojson, dataset = data["geojson"], data["dataset"]

		hist1 = px.histogram(dataset, x="usage", template=template)

		counts = np.histogram(dataset["etages"], bins=[0, 1, 2, 3, 5, 10, 25, 10e9])[0]
		hist2 = px.bar(
			x=["Inconnu", "1", "2", "3 ou 4", "5 à 9", "10 à 24", "25 ou +"], y=counts,
			labels={"x": "etages", "y": "count"}, template=template)

		map_ = px.choropleth_mapbox(
			dataset, geojson=geojson, locations="id", color=dataset["hauteur"], opacity=0.75,
			mapbox_style="carto-darkmatter" if data["dark"] else "carto-positron",
			center={"lon": data["lon"], "lat": data["lat"]}, zoom=15,
			hover_data=["id", "nature", "usage", "etages", "hauteur", "logements"], template=template)
		map_.update_geos(fitbounds="locations", visible=False)
		map_.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

		return [
			dcc.Graph(id="hist1", figure=hist1),
			dcc.Graph(id="hist2", figure=hist2),
			dcc.Graph(id="map", figure=map_),
		]

	@app.callback(
		Output("dark-mode-switch", "on"),
		Input("dark-mode", "modified_timestamp"),
		State("dark-mode", "data")
	)
	def load_dark_mode_status(ts, dark):
		if ts is None:
			raise PreventUpdate
		return dark or False

	@app.callback(
		Output("dark-mode", "data"),
		Input("dark-mode-switch", "on")
	)
	def save_dark_mode_status(dark):
		if dark is None:
			raise PreventUpdate
		return dark

	@app.callback(
		Output("content", "children"),
		Input("size-dropdown", "value"),
		Input("dark-mode", "modified_timestamp"),
		State("dark-mode", "data")
	)
	def update_content(size, ts, dark):
		if size is None and ts is None:
			raise PreventUpdate
		reload_data = False
		if size is not None and size != data["size"]:
			data["size"] = size
			reload_data = True
		if dark is not None:
			data["dark"] = dark
		return content(reload_data)

	app.clientside_callback(
		"""
		function(dark) {
			const themeDark = "https://cdn.jsdelivr.net/npm/bootswatch@5.1.0/dist/darkly/bootstrap.min.css";
			const themeLight = "https://cdn.jsdelivr.net/npm/bootstrap@5.1.0/dist/css/bootstrap.min.css";
			const stylesheetMain = document.querySelector('link[rel=stylesheet][href^="https://cdn.jsdelivr.net/npm/boots"]');
			stylesheetMain.href = dark ? themeDark : themeLight;
			if (dark)
				document.body.classList.add("dark-mode");
			else
				document.body.classList.remove("dark-mode");
		}
		""",
		Output("empty", "children"),
		Input("dark-mode-switch", "on"),
	)

	options = [
		{"label": "25 m", "value": 25},
		{"label": "50 m", "value": 50},
		{"label": "100 m", "value": 100},
		{"label": "250 m", "value": 250},
		{"label": "500 m", "value": 500},
		{"label": "1 km", "value": 1000},
		{"label": "2 km", "value": 2000},
		{"label": "5 km", "value": 5000},
	]
	app.layout = html.Div(children=[
		dcc.Store(id="dark-mode", storage_type="local"),
		daq.BooleanSwitch(id="dark-mode-switch", on=data["dark"]),
		dcc.Dropdown(id="size-dropdown", options=options, value=data["size"], clearable=False, searchable=False),
		html.Div(id="content"),
		# html.H1(
		# 	id="title",
		# 	children=f'Life expectancy vs GDP per capita ({year})',
		# 	style={'textAlign': 'center', 'color': '#7FDBFF'}
		# ),
		# html.Label('Year'),
		# dcc.Dropdown(
		# 	id="year-dropdown",
		# 	options=[{"label": str(y), "value": y} for y in years],
		# 	value=year,
		# ),

		# html.Div(children=f'''
		# 	The graph above shows relationship between life expectancy and
		# 	GDP per capita for year {year}. Each continent data has its own
		# 	colour and symbol size is proportionnal to country population.
		# 	Mouse over for details.
		# '''),
		html.Div(id="empty")
	])

	app.run_server()
