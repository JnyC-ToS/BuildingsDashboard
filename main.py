import plotly_express as px

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from dash_bootstrap_components.themes import DARKLY
import pandas as pd
import requests
import matplotlib.pyplot as plt

if __name__ == '__main__':
	pd.set_option("display.max_columns", None)

	base_url = "https://wxs.ign.fr/essentiels/geoportail/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature" \
	           "&TYPENAME=BDTOPO_V3:batiment&SRSNAME=EPSG:2154&BBOX={xmin},{ymin},{xmax},{ymax},EPSG:2154" \
	           "&STARTINDEX=0&MAXFEATURES=1000&outputFormat=application/json"
	x = 664986.66
	y = 6853924.50
	delta = 500

	url = base_url.format(xmin=x - delta, ymin=y - delta, xmax=x + delta, ymax=y + delta)
	print(f"Requesting URL: {url}")
	req = requests.get(url)
	json_data = req.json()
	# json_data = geojson.loads(req.text)

	# print(json.dumps(json_data["features"], sort_keys=True, indent=4))
	py_data = []
	for feature in json_data["features"]:
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

	data = pd.DataFrame(py_data, columns=["id", "geometry", "nature", "usage", "etages", "hauteur", "logements"])
	# data["usage"].hist()
	# plt.show()
	# usages = data["usage"].unique()
	# count_per_usage = [(usage, data[data["usage"] == usage].count()["id"]) for usage in usages]
	# print(pd.DataFrame(count_per_usage, columns=["type", "count"]))

	app = dash.Dash(__name__, external_stylesheets=[DARKLY])

	# @app.callback(
	# 	[
	# 		Output(component_id="title", component_property="children"),
	# 		Output(component_id="graph1", component_property="figure"),
	# 	],
	# 	[Input(component_id="year-dropdown", component_property="value")]
	# )
	# def update_figure(input_value):
	# 	return [
	# 		f'Life expectancy vs GDP per capita ({input_value})',
	# 		px.scatter(data[input_value], x="gdpPercap", y="lifeExp", color="continent", size="pop",
	# 		           hover_name="country")
	# 	]

	# fig = px.scatter(data[year], x="gdpPercap", y="lifeExp", color="continent", size="pop", hover_name="country")
	hist = px.histogram(data, x="usage", template="plotly_dark")
	map_ = px.choropleth(data, geojson=json_data, locations="id", color=data["hauteur"], featureidkey="properties.district", template="plotly_dark")
	map_.update_geos(fitbounds="locations", visible=False)
	map_.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

	app.layout = html.Div(children=[
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
		dcc.Graph(
			id="hist",
			figure=hist
		),
		dcc.Graph(
			id="map",
			figure=map_
		),
		# html.Div(children=f'''
		# 	The graph above shows relationship between life expectancy and
		# 	GDP per capita for year {year}. Each continent data has its own
		# 	colour and symbol size is proportionnal to country population.
		# 	Mouse over for details.
		# '''),
	])

	app.run_server()
