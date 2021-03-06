import plotly_express as px
import numpy as np
import dash
from dash import dcc
from dash import html
from dash.development.base_component import Component
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_leaflet as dl
from math import cos, radians
import pandas as pd
import requests
import traceback
import sys

from typing import Union


# Constants

base_url = "https://wxs.ign.fr/essentiels/geoportail/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature" \
	"&TYPENAME=BDTOPO_V3:batiment&SRSNAME=EPSG:4326&BBOX={min_lon},{min_lat},{max_lon},{max_lat},EPSG:4326" \
	"&STARTINDEX={offset}&MAXFEATURES=1000&outputFormat=application/json"
dataset_columns = ["id", "geometry", "nature", "usage", "etages", "hauteur", "logements"]


# Data classes and util functions

class Data:
	"""
	Data class to contains Dashboard technical stuff
	"""
	def __init__(self):
		self.dark = True
		self.lon = 0
		self.lat = 0
		self.size = 500
		self.dataset = pd.DataFrame(columns=dataset_columns)
		self.geojson = {"type": "FeatureCollection", "features": []}
		self.error = None


def lon_lat_offset(base_lat: float, size: float) -> (float, float):
	"""
	Convert a distance (in meters) into corresponding longitude and latitude offsets at a given latitude.

	:param base_lat: The latitude where to compute the distance.
	:param size: The distance to convert.
	:return: The corresponding longitude and latitude offsets.
	"""
	offset_lat = size / 111_111
	offset_lon = size / (111_111 * cos(radians(base_lat)))
	return offset_lon, offset_lat


def fetch_data(center_lon: float, center_lat: float, size: float) -> tuple[dict, pd.DataFrame, str]:
	"""
	Fetch data from the API into GeoJSON and Panda DataFrame.

	:param center_lon: The longitude of the center of the area.
	:param center_lat: The latitude of the center of the area.
	:param size: The size of the area.
	:return: The fetched data.
	"""
	offset_lon, offset_lat = lon_lat_offset(center_lat, size / 2)
	min_lon = center_lon - offset_lon
	min_lat = center_lat - offset_lat
	max_lon = center_lon + offset_lon
	max_lat = center_lat + offset_lat

	py_data = []
	json_data = {"type": "FeatureCollection", "features": []}
	error = None

	offset = 0
	fetching = True
	while fetching:
		try:
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
		except requests.ConnectionError:
			error = traceback.format_exc()
			print(f"An error occurred during request: {error}", file=sys.stderr)
			fetching = False

	return json_data, pd.DataFrame(py_data, columns=dataset_columns), error


def histogram(serie: pd.Series, name: str, color: [str], template: str):
	"""
	Generate an histogram using NumPy and Plotly Express from a Panda serie

	:param serie: The data
	:param name: The name of the data
	:param color: The theme color
	:param template: The theme template
	:return: The histogram figure
	"""
	if serie.empty:
		return px.bar(template=template)
	counts, bins = np.histogram(serie[serie.notnull()], bins=range(int(serie.min()), int(serie.max()) + 2))
	bins = 0.5 * (bins[:-1] + bins[1:])
	hist = px.bar(x=bins, y=counts, color_discrete_sequence=color, template=template)
	hist.update_traces(customdata=bins - 0.5, hovertemplate=f"{name} : %{{customdata}}<br>B??timent(s) : %{{y}}")
	return hist


def max_values(serie: pd.Series) -> (float, float):
	"""
	Compute and retrieve de maximum value of a Panda serie

	:param serie: The data
	:return: The maximum value's key and value
	"""
	count = serie.value_counts()
	most_key = 0 if count.empty else count.keys()[0]
	most_val = 0 if count.empty else count[most_key]
	return most_key, most_val


# Main program

if __name__ == "__main__":
	data = Data()

	app = dash.Dash(
		__name__, title="Buildings Dashboard", update_title="Chargement... - Buildings Dashboard",
		external_stylesheets=[dbc.themes.BOOTSTRAP])

	def content(reload_data: bool) -> Union[Component, list[Component]]:
		"""
		Render the content of the Dashboard

		:param reload_data: Whether to force data reload or not
		:return: The content, assignable to an HTML div's children property
		"""

		# Gestion du theme clair/sombre
		dark = data.dark
		template = "plotly_dark" if dark else None
		color = ["#ff59c7"] if dark else ["#9900ff"]
		lon, lat = data.lon, data.lat

		# Chargement de la carte
		if reload_data:
			geojson, dataset, error = data.geojson, data.dataset, data.error = fetch_data(lon, lat, data.size)
		else:
			geojson, dataset, error = data.geojson, data.dataset, data.error

		# Gestion des erreurs de chargement de la carte
		if error:
			return html.P([
				html.Strong("Une erreur est survenue :"),
				html.Pre(f"{error}")
			], id="data-info", className="pb-4")

		buildings_count = len(dataset)
		if buildings_count == 0:
			return html.P([
				"Coordonn??es de la zone (lon, lat) : (",
				html.Strong(f"{lon:.5f}"),
				", ",
				html.Strong(f"{lat:.5f}"),
				")",
				html.Br(),
				"Aucun b??timent pr??sent dans la zone. Avez-vous cliqu?? en France ?",
				html.Br(),
				"Essayez ",
				html.Strong("un autre endroit"),
				" ou ",
				html.Strong("une autre taille"),
				"."
			], id="data-info", className="pb-4")

		data_info = [
			"Coordonn??es de la zone (lon, lat) : (",
			html.Strong(f"{lon:.5f}"),
			", ",
			html.Strong(f"{lat:.5f}"),
			")",
			html.Br(),
			"B??timents dans la zone : ",
			html.Strong(str(buildings_count))
		]

		etages = dataset["etages"]
		hist_etages = histogram(etages, "??tage(s)", color, template)
		hist_etages.update_layout(
			title={
				"text": "Nombre de b??timents en fonction de leur nombre d'??tages",
				"y": 0.9,
				"x": 0.5,
				"xanchor": "center",
				"yanchor": "bottom"
			},
			xaxis_title_text="Nombre d'??tages",
			yaxis_title_text="Nombre de b??timents",
			bargap=0
		)

		etages_most_key, etages_most_val = max_values(etages)
		hist_etages_analyse = [
			"Cet histogramme repr??sente la distribution des b??timents en fonction de leur nombre d'??tages.",
			html.Br(),
			"Les b??timents ont entre ",
			html.Strong(f"{etages.min():n}"),
			" et ",
			html.Strong(f"{etages.max():n}"),
			" ??tage(s), et en moyenne ",
			html.Strong(f"{etages.mean():.1f}"),
			".",
			html.Br(),
			"Le nombre d'??tages poss??d?? par le plus de b??timents est ",
			html.Strong(f"{etages_most_key:n}"),
			" (avec ",
			html.Strong(f"{etages_most_val:n}"),
			" b??timents).",
			html.Br(),
			"Un b??timent ayant 0 ??tage est soit un b??timent d'usage ",
			html.Strong("Annexe"),
			" soit une construction l??g??re, ou bien la donn??e est absente (b??timent inconnu).",
		]

		logements = dataset["logements"]
		hist_logements = histogram(logements, "Logement(s)", color, template)
		hist_logements.update_layout(
			title={
				"text": "Nombre de b??timents en fonction de leur nombre de logements",
				"y": 0.9,
				"x": 0.5,
				"xanchor": "center",
				"yanchor": "bottom"
			},
			xaxis_title_text="Nombre de logements",
			yaxis_title_text="Nombre de b??timents",
			bargap=0
		)

		logements_most_key, logements_most_val = max_values(logements)
		logements_notnull = logements[logements != 0]
		logements_notnull_most_key, logements_notnull_most_val = max_values(logements_notnull)
		hist_logements_analyse = [
			"Cet histogramme repr??sente la distribution des b??timents en fonction de leur nombre de logement",
			html.Br(),
			"Les b??timents ont entre ",
			html.Strong(f"{logements.min():n}"),
			" et ",
			html.Strong(f"{logements.max():n}"),
			" logement(s),",
			" et en moyenne ",
			html.Strong(f"{logements.mean():.1f}"),
			".",
			html.Br(),
			"Le nombre de logement poss??d?? par le plus de b??timents est ",
			html.Strong(f"{logements_most_key:n}"),
			" (avec ",
			html.Strong(f"{logements_most_val:n}"),
			" b??timents).",
			html.Br(),
			"Un b??timent ayant 0 logement est soit un b??timent d'usage ",
			html.Strong("Annexe"),
			" soit une construction l??g??re, soit d'un type autre que r??sidentiel (commercial, sportif, religieux, etc...).",
			html.Br(),
			"La moyenne de logements par b??timent sans ceux ?? 0 est de ",
			html.Strong(f"{logements_notnull.mean():.1f}"),
			".",
			html.Br(),
			"Le nombre de logement poss??d?? par le plus de b??timents hormis 0 est ",
			html.Strong(f"{logements_notnull_most_key:n}"),
			" (avec ",
			html.Strong(f"{logements_notnull_most_val:n}"),
			" b??timents).",
		]

		graph_usages = px.histogram(dataset, x="usage", color_discrete_sequence=color, template=template)
		graph_usages.update_traces(hovertemplate="Usage : %{x}<br>B??timent(s) : %{y}")
		graph_usages.update_layout(
			title={
				"text": "R??partition de l'usage des b??timents",
				"y": 0.9,
				"x": 0.5,
				"xanchor": "center",
				"yanchor": "bottom"
			},
			xaxis_title_text="Type de b??timent",
			yaxis_title_text="Nombre de b??timents"
		)

		usages_most_key, usages_most_val = max_values(dataset["usage"])
		graph_usages_analyse = [
			"Ce graphique repr??sente la r??partition de l'usage des b??timents. Contrairement au champ ",
			html.Strong("Nature"),
			" (bas?? uniquement sur l'apparence), elle est repr??sentative de l'utilisation actuelle du b??timent.",
			html.Br(),
			"L'usage le plus repr??sent?? est ",
			html.Strong(usages_most_key),
			" (avec ",
			html.Strong(f"{usages_most_val:n}"),
			" b??timents).",
			html.Br(),
			"Un b??timent d'usage ",
			html.Strong("Indiff??renci??"),
			" est un b??timent d'usage inconnu."
		]

		map_buildings = px.choropleth_mapbox(
			dataset, geojson=geojson, locations="id", color=dataset["hauteur"], opacity=0.75,
			mapbox_style="carto-darkmatter" if dark else "carto-positron", height=800,
			center={"lon": data.lon, "lat": data.lat}, zoom=15, template=template)
		map_buildings.update_traces(
			customdata=dataset.fillna("<i>Donn??e absente</i>"),
			hovertemplate="<br>".join([
				"<b>ID : %{customdata[0]}</b>",
				"Nature : %{customdata[2]}",
				"Usage : %{customdata[3]}",
				"??tage(s) : %{customdata[4]}",
				"Hauteur : %{customdata[5]}",
				"Logement(s) : %{customdata[6]}"
			]))
		map_buildings.update_geos(fitbounds="locations", visible=False)
		map_buildings.update_layout(
			title={
				"text": "G??o-visualisation des b??timents avec leur hauteur",
				"y": 0.92,
				"x": 0.5,
				"xanchor": "center",
				"yanchor": "bottom",
				"font": {"size": 24}
			},
			margin={"r": 0, "t": 0, "l": 0, "b": 0}
		)

		hauteur = dataset["hauteur"]
		hauteur_notnull = hauteur[hauteur != 0]
		map_buildings_analyse = [
			"Les b??timents sont repr??sent??s par la forme g??n??rale de leur toiture projet??s en 2D au sol. "
			"Leur couleur repr??sente une ??chelle de hauteur sur les b??timents pr??sents dans la zone, "
			"bas?? sur le plus haut b??timent pr??sent",
			html.Br(),
			"Les b??timents font entre ",
			html.Strong(f"{hauteur.min():.1f}"),
			" et ",
			html.Strong(f"{hauteur.max():.1f}"),
			" m??tre(s) de hauteur,",
			" et en moyenne ",
			html.Strong(f"{hauteur.mean():.2f}"),
			"m.",
			html.Br(),
			"La valeur 0 signifie que la hauteur n'est pas connue.",
			html.Br(),
			"La moyenne de hauteur des b??timents sans les valeurs ?? 0 est de ",
			html.Strong(f"{hauteur_notnull.mean():.2f}"),
			"m."
		]

		return [
			html.P(data_info, id="data-info", className="pb-4"),
			dbc.Row([
				dbc.Col([
					dcc.Graph(figure=hist_etages, id="hist-etages", className="pb-4"),
					html.P(hist_etages_analyse, id="hist-etages-analyse", className="data-analyse")
				], width=6),
				dbc.Col([
					dcc.Graph(figure=hist_logements, id="hist-logements", className="pb-4"),
					html.P(hist_logements_analyse, id="hist-logements-analyse", className="data-analyse")
				], width=6)
			], className="pb-4"),
			dcc.Graph(figure=graph_usages, id="graph-usages", className="pb-4"),
			html.P(graph_usages_analyse, id="graph-usages-analyse", className="data-analyse pb-4"),
			dcc.Graph(figure=map_buildings, id="map-buildings", className="pb-4"),
			html.P(map_buildings_analyse, id="map-buildings-analyse", className="data-analyse pb-4")
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
		Output("dashboard-content", "children"),
		Input("size-dropdown", "value"),
		Input("map-home", "click_lat_lng"),
		Input("dark-mode", "modified_timestamp"),
		State("dark-mode", "data")
	)
	def update_content(size, coords, ts, dark):
		if ts is None or (size == data.size and coords == [data.lat, data.lon] and dark == data.dark):
			raise PreventUpdate
		reload_data = False
		if size is not None and size != data.size:
			data.size = size
			reload_data = True
		if coords is not None and coords != [data.lat, data.lon]:
			data.lat, data.lon = coords
			reload_data = True
		if dark is not None and dark != data.dark:
			data.dark = dark
		return content(reload_data)

	@app.callback(
		Output("map-home-layer-dark", "zIndex"),
		Output("map-home-layer-light", "zIndex"),
		Input("dark-mode", "modified_timestamp"),
		State("dark-mode", "data")
	)
	def update_homemap(ts, dark):
		if ts is None:
			raise PreventUpdate
		return [2, 1] if dark else [1, 2]

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

	@app.callback(
		Output("info-modal", "is_open"),
		Input("info-modal-open", "n_clicks"),
		Input("info-modal-close", "n_clicks"),
		State("info-modal", "is_open")
	)
	def toggle_modal(n1, n2, is_open):
		if n1 or n2:
			return not is_open
		return is_open

	@app.callback(
		Output("map-div", "className"),
		Output("dashboard", "className"),
		Input("map-home", "click_lat_lng"),
		Input("back-to-map", "n_clicks")
	)
	def toggle_map(coords, back):
		if coords is not None and coords != [data.lat, data.lon]:
			return ["d-none", None]
		if back is not None:
			return [None, "d-none"]
		raise PreventUpdate

	header = html.Header([
		dbc.Row([
			dbc.Col(dbc.Button("??? S??lection de la zone", id="back-to-map"), align="center"),
			dbc.Col(html.H1("Buildings Dashboard", className="text-center"), align="center"),
			dbc.Col(html.Div([
				dcc.Dropdown(id="size-dropdown", options=[
					{"label": "25 m", "value": 25},
					{"label": "50 m", "value": 50},
					{"label": "100 m", "value": 100},
					{"label": "250 m", "value": 250},
					{"label": "500 m", "value": 500},
					{"label": "1 km", "value": 1000},
					{"label": "2 km", "value": 2000},
					{"label": "5 km", "value": 5000},
				], value=data.size, clearable=False, searchable=False),
				# Bouton Information
				dbc.Button("INFO", id="info-modal-open"),
				dbc.Modal([
					dbc.ModalHeader(dbc.ModalTitle("Informations sur le Dashboard")),
					dbc.ModalBody([
						html.H3("Les donn??es"),
						html.P("""
							Les donn??es exploit??es sont issues de la BDTOPO v3 de l'IGN (Institut National de
							l'Information G??ographique et Foresti??re). Ces donn??es sont devenues libres d'acc??s il y a
							peu de temps, et sont accessibles ?? travers le G??oPortail, sous forme de flux WXS.
						"""),
						html.P("""
							Ce qui nous int??resse ici est un flux de donn??es vecteur en WFS de la ressource
							\"BDTOPO_V3:batiment\". La documentation est disponible en ligne sur le site G??oServices,
							?? travers notamment, le descriptif de contenu de la BDTOPO v3 (section 8.2 BATIMENT).
						"""),
						html.H3("Les interactions"),
						html.P("""
							Depuis la carte sur laquelle on arrive pour s??lectionner une zone, il est possible de se
							d??placer puis de cliquer sur l'endroit dont on souhaite explorer les b??timents. Une fois
							sur le dashboard, si la zone est trop petite, il est possible d'affiner le rayon avec le
							menu d??roulant, cependant charger une plus grande zone va demander plus de temps."""),
						html.P("""
							Le dashboard dispose d'un th??me clair, en blanc et violet, ainsi que d'un th??me sombre, en
							noir et rose. Ce th??me est contr??llable ?? partir du bouton en haut ?? droite. Les graphiques
							et les cartes vont se mettre ?? jour en conformit?? avec le th??me s??lectionn??e."""),
						html.P("""
							Enfin, il est possible d'interagir avec les graphiques en s??lectionnant des zones, exporter
							des images, etc... gr??ce aux boutons directement pr??sents en haut ?? droite de chacun.
						"""),
						html.H3("?? propos"),
						html.P("""
							Ce dashboard a ??t?? r??alis?? par Jenny CAO et Th??o SZANTO dans le cadre d'un projet en 3??me
							ann??e d'??cole d'ing??nieur ?? ESIEE Paris."""),
						html.P("""Le choix des donn??es ??tait libre, cependant elles
							devaient ??tre accessibles en Open Data, pouvoir ??tre repr??sentable sur une carte, et le
							dashboard devait inclure au moins un histogramme. Enfin, elles devaient ??tre charg??es
							dynamiquement si possible selon des actions de l'utilisateur.
						""")
					]),
					dbc.ModalFooter(dbc.Button("Fermer", id="info-modal-close"))
				], id="info-modal", is_open=False),
				html.Span("????", className="dark-mode-emoji"),
				daq.BooleanSwitch(id="dark-mode-switch", on=data.dark, color="#ff59c7", className="py-1"),
				html.Span("????", className="dark-mode-emoji")
			], className="d-flex justify-content-end"), align="center")
		], className="justify-content-between py-2")
	], id="header", className="container-fluid px-4 fixed-top")

	france_bounds = [[51.197749, -5.386891], [41.325451, 9.627019]]
	homemap = html.Div(dcc.Loading([
		html.P("Cliquez en France sur la carte pour s??lectionner le centre de la zone", id="map-home-help"),
		dl.Map([
			dl.TileLayer(id="map-home-layer-light", bounds=france_bounds),
			dl.TileLayer(
				id="map-home-layer-dark",
				url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png",
				attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>',
				bounds=france_bounds
			)
		], id="map-home", style={
			"width": "100vw",
			"height": "100vh"
		}, center=[46.884224, 2.438964], bounds=france_bounds, zoom=7)
	], type="circle"), id="map-div")

	dashboard = html.Div([
		header,
		html.Main(dcc.Loading(html.Div(id="dashboard-content"), type="circle"), id="main", className="container-fluid px-4"),
	], id="dashboard", className="d-none")

	app.layout = html.Div([
		dcc.Store(id="dark-mode", storage_type="local"),
		homemap,
		dashboard,
		html.Div(id="empty")
	])

	app.run_server()
