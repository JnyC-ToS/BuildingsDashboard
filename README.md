# Buildings Dashboard
Dashboard Python pour visualiser des données à propos des bâtiments de la France.

## Rapport d'analyse
Des informations à propos de l'utilisation du Dashboard sont disponibles directement dedans à l'aide du bouton `INFO` en haut à droite (nécessite d'avoir au préalable cliqué sur un zone de la carte pour accéder au Dashboard).
Des analyses à propos des graphiques sont disponibles directement en dessous de ces derniers, et s'adaptent selon les valeurs.

## User Guide
Il est nécessaire d'installer au préalable Python 3 ainsi que l'utilitaire `pip`.
Les commandes faisant référence à ce dernier utilisent `pip`, cependant, il peut être nécessaire d'utiliser `pip3` sous Linux pour obtenir la bonne version.

### Installation des dépendances
Tous les modules nécessaires sont listés dans le fichier `requirements.txt` :
```sh
pip -install -r requirements.txt
```

<details>
<summary>Liste des packages qui seront installés</summary>

```requirements.txt
# Dépendances directes
dash~=2.0.0
pandas~=1.3.5
requests~=2.26.0
dash-bootstrap-components~=1.0.2
numpy==1.22.0
dash_leaflet~=0.1.23
plotly-express~=0.4.1
dash_daq~=0.5.0

# Dépendances transitives
dash-table==5.0.0
Flask>=1.0.4
dash-html-components==2.0.0
dash-core-components==2.0.0
plotly>=5.0.0
flask-compress
python-dateutil>=2.7.3
pytz>=2017.3
certifi>=2017.4.17
urllib3<1.27,>=1.21.1
charset-normalizer~=2.0.0; python_version >= "3"
idna<4,>=2.5; python_version >= "3"
geobuf
scipy>=0.18
statsmodels>=0.9.0
patsy>=0.5
itsdangerous>=2.0
Jinja2>=3.0
Werkzeug>=2.0
click>=7.1.2
tenacity>=6.2.0
six
brotli
protobuf
MarkupSafe>=2.0
```
</details>

Pour lancer le Dashboard, il faut exécuter le fichier `main.py`. Là encore, il peut être nécessaire d'utiliser la commande `python3` plutôt que `python`.
```sh
python main.py
```

Le Dashboard est alors accessible depuis votre navigateur à l'URL : http://127.0.0.1:8050/.

## Developer Guide
Tout le code du Dashboard est dans le fichier `main.py` et le style dans `assets/style.css`.

### La récupuration des données
Elle se fait par le biais de la fonction `fetch_data` qui va faire une requête GET à l'URL contenant les données et les mettre dans des variables utilisable par le code (collection GéoJSON et DataFrame Panda).

### Le calcul des figures
La fonction `histogram` permet la construction d'un histogramme à partir des données. 
La fonction `max_values` va permettre de récupérer les valeurs maximales d'une série de données (utile notamment dans le rapport d'analyse).

### La structure du Dashboard
Il est d'abord nécessaire de cliquer sur la carte pour sélectionner la zone.
Ceci est réalisé à l'aide de Dash-Leaflet.

L'en-tête du Dashboard est composé du titre, de quelques boutons, et du menu déroulant de sélection de la taille de la zone.

Le corps du Dashboard est composé de :
- Gestion du thème clair et sombre ;
- Génération de la carte et du clic sur la carte ;
- Organisation des données : Coordonnées de la zone, bâtiment dans la zone ;
- Gestion de l'affichage des histogrammes et barchart et leur rapport d'analyse ;
- Resprésentation géographique des bâtiments étalonner sur les échelle de couleur par raport à leur hauteur ;
- Le rapport d'analyse de la carte.
