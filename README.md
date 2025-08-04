# Urban-Climate-Analyzer

Dieses Projekt umfasst ein Python-basiertes Analysewerkzeug zur Durchführung stadtklimatischer Auswertungen. Ziel ist es, mithilfe von Geodaten (u.a. Satellitenbilder, Wetterdaten, Landnutzungskartierungen) und GIS-gestützten Workflows tiefere Einblicke in urbane Klimaeffekte zu gewinnen. Zur Unterstützung der kommunalen Stadtplanung werden die Ergebnisse durch topografische Analysen ergänzt. So lassen sich z. B. Kaltluftentstehungsgebiete mit einer relevanten Hangneigung (> 2°) gezielt extrahieren, um klimatische Fließprozesse besser zu verstehen. Das Tool identifiziert unter anderem: städtische Hitzeinseln (Urban Heat Islands), Vegetationszustände inklusive Feuchtigkeitsindikatoren, potenzielle Kaltluftentstehungsgebiete, sowie Luftfließrichtungen in Abhängigkeit der Topografie. 

# Überblick des Analysewerkzeuges

### Analysemodule
Die Funktionalität zur Durchführung stadtklimatischer Analyse ist modular aufgebaut. Jedes Modul kann eigenständig und unabhängig für beliebige Kommunen ausgeführt werden. Folgende Analysemodule stehen zur Verfügung:
* Hitzeinseln (Land Surface Temperature)
* Vegetationsindizes (NDVI, NDMI)
* Potenzielle Kaltluftentstehungsgebiete
* Potenzielle Kaltluftentstehungsgebiete mit Hangneigung
* Fließrichtung (Luftströmungsanalyse)

Die Analyseergebnisse werden als Raster- und Vektordaten in einem lokal Ergebnisordner bereitgestellt und über eine integrierte GeoServer-Instanz zur weiteren Nutzung verfügbar gemacht.

### Verwendete Datensätze
Für die Auswertung der oben genannten Module werden zahlreiche Datenquellen herangezogen. Im folgenden wird ein kurzer Überblick über diese und deren Nutzung in den einzelnen Analysemodulen vorgestellt. Die Konfiguration der jeweiligen Datenquelle wird in Abschnitt (*Konfiguration*) ausführlicher beschrieben.

- **Multispektrale Satellitendaten** der Landsat 8 (NASA) und Sentinel-2 (ESA) Mission werden verwendet. Landsat 8 wird zur Berechnung der Landoberflächentemperatur (LST) genutzt, während Sentinel-2-Daten zur Ermittlung von Vegetationsindizes dienen. Die Daten werden über die Schnittstelle von SentinelHub bezogen und ein entsprechender Account (https://www.sentinel-hub.com/) wird benötigt. Eingesetzt in:
    - Hitzeinseln (Land Surface Temperature)
    - Vegetationsindizes (NDVI, NDMI)
    
- **Meteorologische Daten** wie Temperatur und Windgeschwindigkeit werden vom Deutschen Wetterdienst (DWD) bezogen. Sie unterstützen die Auswahl geeigneter Satellitenbilder und fließen in folgende Module ein:
    - Hitzeinseln (Land Surface Temperature)
    - Vegetationsindizes (NDVI, NDMI)

- **Landnutzungskartierungen** mit Informationen aus OpenStreetMap, Corine Land Cover Datensätzen und Grünlandkartierungen (NRW) dienen der Erkennung potenzieller Kaltluftentstehungsgebiete. Diese Daten werden automatisch geladen, sobald das entsprechende Modul ausgeführt wird.
    - Kaltluftentstehungsgebiet

- **Topografische Daten** wie ein Digitales Geländemodell (DGM) oder ein Digitales Höhenmodell (DHM) werden zur Ableitung von Hangneigung und Fließrichtung von Topografische Daten verwendet. Diese Daten müssen durch die Nutzer:innen bereitgestellt werden, da sie bundesweit nicht einheitlich und hoher Auflösung verfügbar sind. Eingesetzt in:
    - Potenzielle Kaltluftentstehungsgebiete mit Hangneigung
    - Fließrichtung

### Docker-Container
Das Analyse-Tool sowie der GeoServer werden zusätzlich als Docker-Container bereitgestellt. Die Konfiguration der Komponenten kann in der docker-compose Datei vorgenommen werden. Der Aufruf des Tools über Docker wird in den folgenden Abschnitten genauer beschrieben.

Hinweis: Bei dem Produktivbetrieb ist sicherzustellen, dass die ports der container korrekt exponiert sind und die Services nur zur innerhalb des Docker-Netzes erreichbar sind (z.B. mit 'expose' anstatt 'ports').


# Konfiguration des Analysewerkzeuges

Die Konfiguration des Analyse-Tools erfolgt in drei Ebenen:

- Sensible Zugangsdaten (.env)
- Stadt-/Projekt-spezifische Einstellungen (config/<stadt>.yaml)
- Globale Einstellungen und Analyseparameter (app.config)

## Konfiguration der API-Zugangsdaten

Sensible Informationen, wie API-Zugangsdaten und Zugriffe auf den GeoServer sowie die PostGIS-Datenbank, werden in einer .env-Datei gepflegt.

Beispiel ```.env```:
```
# Zugangsdaten für den Zugriff auf Sentinel Hub API
SH_CLIENT_ID=your_client_id_here
SH_CLIENT_SECRET=your_client_secret_here

# Zugangsdaten für die Authentifizierung am GeoServer (Optional, nicht benötigt zur Analyse)
GEOSERVER_ADMIN_USER=admin
GEOSERVER_ADMIN_PASSWORD=your_password_here
GEOSERVER_PORT=8080
GEOSERVER_WORKSPACE=urban_climate_workspace
GEOSERVER_HOST=geoserver

# Zugangsdaten für die Authentifizierung an der PostGIS-DB (Optional, nicht benötigt zur Analyse)
POSTGRES_USER=postgres_user
POSTGRES_PASSWORD=postgres_password
POSTGRES_DB=UCA_DB
POSTGRES_PORT=5432
```

Hinweis: Wenn Satellitendaten von Sentinel bezogen werden sollen, ist ein aktives Konto bei Sentinel Hub erforderlich.

## Konfiguration je Untersuchungsgebiet ('config/stadt.yaml')

Für jede Stadt oder jedes Untersuchungsgebiet wird eine eigene Konfigurationsdatei benötigt. Diese Datei enthält sämtliche projektspezifischen Einstellungen wie z. B. Geometrien, Datenquellen oder lokale Pfade. Dadurch wird eine modulare und wiederholbare Analyse verschiedener Kommunen ermöglicht.

Beispiel: ```config/paderborn.yaml```:
```
aoi:
  city_name: "Paderborn"              # Stadtname als Referenz
  polygon_buffer_in_meter: 8000       # Optionaler Puffer (z. B. 8 km) um Stadtgrenze

data_sources:
  dwd_weatherstation_filename_recent: "tageswerte_KL_03028_akt.zip"       # Aktuelle Wetterdaten DWD
  dwd_weatherstation_filename_historical: "tageswerte_KL_03028_19510101_20241231_hist.zip"  # Historische Wetterdaten
  local_dem_data_dirs: 
    - "/data/dgm"                    # Lokale Pfade zu topografischen Daten (DGM/DOM)
```

Pflichtangaben je Stadt:
- Gebietsauswahl (AOI):
    - entweder als Stadtname (city_name) mit definierbarem Puffer (polygon_buffer_in_meter)
    - oder alternativ per Bounding Box (Koordinaten in EPSG:4326, nicht im obigen Beispiel enthalten)

Ooptionale Angaben, aber erforderlich für bestimmte Module je Stadt:
- Wetterstation: Angabe der DWD-Station (z. B. 03028 für Paderborn) mit dazugehörigen Datendateien sofern Satellitenbilder ausgewertet sollen (Modul Hitzinseln und Vegetationsindices)
- Topografie (optional, aber erforderlich für bestimmte Module):
    Pfade zum Digitalen Höhenmodell (DHM) und/oder Digitalen Geländemodell (DGM), falls Module wie Fließrichtung oder Kaltluft mit Hangneigung verwendet werden sollen


## Globale Konfiguration des Tools(app.config)
Allgemeine Parameter, URLs zu OpenData-Quellen und Analyseeinstellungen werden zentral in der Datei app.config hinterlegt. Diese Werte gelten für alle Projekte, können aber bei Bedarf von fortgeschrittenen Nutzern angepasst werden.

Beispiel: ```config/app.yaml```:
```
data_sources:
  dwd_url_recent_data: "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent/"
  dwd_url_historical_data: "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/historical/"
  dataset_url_clc: "https://daten.gdz.bkg.bund.de/produkte/dlm/clc5_2018/aktuell/clc5_2018.utm32s.shape.zip"
  dataset_url_dgl: "https://www.opengeodata.nrw.de/produkte/umwelt_klima/bodennutzung/landwirtschaft/DGL_EPSG25832_Shape.zip"

thresholds:
  date_filter:
    max_windspeed: 2.6            # Maximal erlaubte Windgeschwindigkeit (m/s) zur Auswahl geeigneter Tage
    min_temperature: 25.0         # Mindesttemperatur (°C) zur Auswahl heißer Tage
  satellite_filter:
    max_cloud_coverage: 25        # Maximale Wolkenbedeckung (%) für Satellitenbildauswahl
  historical_processing:     
    starting_year_from: "01.01.2023"  # Startzeitpunkt für historische Auswertungen

output_data_dir: "./../data/"              # Speicherort für Analyseergebnisse
```

Erläuterung der zentralen Parameter:
- data_sources: URLs zu öffentlichen Datenportalen (DWD, CLC, DGL etc.)
- thresholds.date_filter: Regeln zur Auswahl klimatypischer Tage für die Analyse
- thresholds.satellite_filter: Qualitätsfilter zur Bildauswahl (z. B. maximale Wolkendecke)
- thresholds.historical_processing: Startzeitpunkt für die Verarbeitung historischer Datensätze
- output_data_dir: Zentrales Ergebnisverzeichnis (siehe Kapitel „Ergebnisstruktur“)

**Hinweis**:
In der Regel ist eine Änderung dieser Datei nicht notwendig. Für erfahrene Nutzer ist jedoch eine Feinjustierung möglich – insbesondere, wenn z. B. zu wenige geeignete Satellitenbilder gefunden werden oder andere Schwellenwerte erforderlich sind.

# Aufruf des Tools

## Lokale Ausführung

### Vorbereitung der Umgebung
Vor der Ausführung muss die lokale Python-Umgebung vorbereitet werden:

Virtuelle Umgebung erstellen (empfohlen)
```
python -m venv .venv
source .venv/bin/activate  # unter Windows: .venv\Scripts\activate
```

Abhängigkeiten installieren
```
pip install -r requirements.txt
```

### Ausführung

Das Tool wird über das Python-Skript main.py im Ordner 'src' aufgerufen und benötigt mindestens den Namen der Stadt (bzw. den Namen der Konfigurationsdatei) sowie eines oder mehrerer Module, die ausgeführt werden sollen.

```
cd src/
python main.py --city <STADT> [OPTIONEN] --modules <MODULNAME>
```

Dabei können die folgenden Optionen übergeben werden

| Parameter                   | Beschreibung                                                                             |
| --------------------------- | ---------------------------------------------------------------------------------------- |
| `--city <NAME>`             | **(Pflichtfeld)** Name der Stadt/Kommune, entsprechend einer Datei `config/<NAME>.yaml`. |
| `--modules <MODUL[,MODUL]>` | Liste der zu analysierenden Module (siehe Tabelle oben). `all` für vollständige Analyse. |
| `--use_historical_data`     | Optional. Bezieht auch historische Wetterdaten aus DWD-Archiven.                         |
| `--upload_to_geoserver`     | Optional. Stellt die Ergebnisse automatisch im GeoServer bereit.                         |
| `--override_existing_data`  | Optional. Überschreibt bereits vorhandene Ergebnisdaten im lokalen Ergebnisverzeichnis.  |
| `-h`, `--help`              | Zeigt Hilfe zur Nutzung und verfügbaren Parametern an.                                   |


Die Analysemodule können wie folgt an das Tool übergeben werden:

| Modul                    |  Kürzere Version | Deutsche Alternative   |
| ------------------------ |  --------------- | ---------------------- |
| Land Surface Temperature |  `lst`           | `hitzeinseln`          |
| Vegetation Indices       |  `veg`           | `vegetation`           |
| Cold Air Zones           |  `cold`          | `kaltluft`             |
| Cold Air Zones + Slope   |  `cold_slope`    | `kaltluft_hangneigung` |
| Flow Direction           |  `flow`          | `flussrichtung`        |
| Alle Module              |  `all`           | `alle`                 |


### Beispielaufrufe
Die folgenden Beispielaufrufen zeigen den Aufruf mit Modulen und Optionen auf: 

```
python main.py --city paderborn --modules lst
```
Führt nur das Modul für Land Surface Temperature aus.

```
python main.py --city paderborn --modules lst,cold,flow
```
Führt die Module Hitzeinseln, Kaltluftgebiete und Fließrichtung aus.

```
python main.py --city paderborn --modules all --use_historical_data --upload_to_geoserver --override_existing_data
```

Führt alle Module aus, inklusive: Historischer Wetterdatenverarbeitung, Upload der Ergebnisse auf den GeoServer, Überschreiben bereits vorhandener Ergebnisse

## Ausführung im Docker Container

Das Tool kann auch innerhalb eines Docker-Containers ausgeführt werden. Sofern ein Hosting der Analyseergebnisse in einer GeoServer- und DatenbankInstanz erwünscht sind, ist Ausführung der über docker compose zwingend notwendig. 

### Aufruf der Analyse im Container

Die Analyse kann wie im lokalen Beispiel, jedoch isoliert im Container ausgeführt werden (z. B. für Kaltluftentstehungsgebiete):
```
docker compose run --rm --build climate_analysis python main.py --city paderborn --modules cold
```
Alternativ, ohne das Image neu zu bauen:
```
docker compose run --rm climate_analysis python main.py --city paderborn --modules lst,cold,flow
```
Hinweis: Das --build-Flag sorgt dafür, dass das Docker-Image vor der Ausführung neu gebaut wird.


### Aufruf der Analyse im Container für die Bereitstellung in Geoserver und PostGIS

Falls die Ergebnisse per GeoServer und PostGIS bereitgestellt werden sollen, müssen diese Dienste zuerst gestartet werden:
```
docker compose up -d --build geoserver postgis
```
Dadurch werden die PostGIS-Datenbank und die GeoServer-Instanz im Hintergrund gestartet. Der GeoServer ist anschließend unter http://localhost:8080/geoserver erreichbar (sofern nicht anders konfiguriert).

Anschließend kann die Analyse im Docker-Container durchgeführt werden. Mit der Option 'upload_to_geoserver' werden die Ergebnisdaten im Geoserver veröffentlicht: 
```
docker compose run --rm climate_analysis python main.py --city paderborn --modules lst --upload_to_geoserver 
```

Hinweis: Die Analyse kann bereits vorab ausgeführt werden (lokal oder im Docker container). Mit der Option --upload_to_geoserver lassen sich vorhandene Ergebnisse nachträglich veröffentlichen.


# Struktur der Dateiordner:

In dem Verzeichnis /data werden Datensätze, temporäre und lokale Ergebnisdaten gespeichert.

### Ergebnis-Ordner
Die Ergebnisse der Analysen werden modulweise je Untersuchungsgebiet (der angegebene Name unter --city) im Ordner results/ abgelegt. Jedes Modul erzeugt eigene Geodatenformate (Raster- oder Vektordaten), die zur Weiterverarbeitung oder Visualisierung genutzt werden können. Die Ordnerstruktur innerhalb des Ergebnisverzeichnisses ist wie folgt aufgebaut.

```
rustuls/
└── city_name/
    ├── cold_air_zones/
    │   ├── cold_air_zones.gpkg
    │
    ├── cold_air_zones_with_slope/
    │   └── cold_air_zones_with_slope.gpkg
    │
    ├── flow_direction/
    │   └── flow_direction_100_dir_name_dem.gpkg
    │
    ├── heat_islands/
    │   └── lst/
    │       ├── timesteps/
    │       │   └── 20230401_lst.tif
    │       └── aggregates/
    │           ├── yearly/
    │           │   └── 2023_lst.tif
    │           └── monthly/
    │               └── 2023_04_lst.tif
    │
    └── vegetation_indices/
        ├── ndvi/
        │   ├── timesteps/
        │   │   └── 20230401_ndvi.tif
        │   └── aggregates/
        │       ├── yearly/
        │       │   └── 2023_ndvi.tif
        │       └── monthly/
        │           └── 2023_04_ndvi.tif
        └── ndmi/
            ├── timesteps/
            │   └── 20230401_ndmi.tif
            └── aggregates/
                ├── yearly/
                │   └── 2023_ndmi.tif
                └── monthly/
                    └── 2023_04_ndmi.tif


```
Für die Module Land Surface Temperature und Vegetationsindizes werden sowohl Zeitreihen-Daten (timesteps) als auch aggregierte Auswertungen (monatlich und jährlich) bereitgestellt. So lassen sich sowohl kurzfristige Schwankungen als auch langfristige Trends analysieren.

### Weitere Order unter /data

**Datasets**: In Datasets werden Geodatensätze lokal vorgehalten die regionsübergreifend eingesetzt werden. 

**Downloads**: In Downloads werden heruntergeladene Satellitenbilder und Wetterdaten gespeichert. Bei mehrmaligen Aufruf der Module werden vorhandene Daten nicht erneut heruntergeladen. 

**Processing-Order** In Processing werden Zwischenberechnungen der einzelnen Module gespeichert. Die Eregbnisdaten werden beim erneuten Aufrauf der Module wiederverwendet. 

## Contact
E-Mail: info[at]vision-impulse.com

## Rechtliches

&copy; 2025 Vision Impulse GmbH • Lizenz: [AGPLv3](LICENSE)  
Umsetzung durch [Vision Impulse GmbH](https://www.vision-impulse.com)