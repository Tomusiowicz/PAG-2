import requests
import zipfile
import io
import os
import pandas as pd
import geopandas as gpd
import numpy as np
import pandas as pd

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import redis
from redis.commands.search.field import GeoShapeField, TextField
from redis.commands.search.indexDefinition import IndexType, IndexDefinition
from redis.commands.search.query import Query
from redis.commands.search import Search

import re

#funkcje redis
def connect_redis_db(host:str, port:int, password:str) -> redis.Redis:
    pool = redis.ConnectionPool (host=host, port=port, password=password)
    db = redis.Redis(connection_pool=pool)
    return db

def create_geospatial_index(db:redis.Redis) -> Search:
    try:
        db.ft("idx:stations").info() #wyrzuca wyjatek jezeli nie ma indeksu
        index = db.ft("idx:stations")
        print("indeks stations juz istnieje")

    except Exception as e:
        print("indeks stations nie istnieje", e)
        schema = (TextField("name", as_name='name'),
                    GeoShapeField("geom", as_name="geom")) #indeksowanie po polu geo
        index = db.ft("idx:stations")
        index.create_index(
            schema,
            definition=IndexDefinition(
            prefix=["station:"], index_type=IndexType.HASH
            )
        )
    return index

def load_station_data_into_redis(station_geodf:gpd.GeoDataFrame, db:redis.Redis):
    #convert crs to wgs84
    station_geodf.to_crs(epsg='4326',inplace = True)
    station_geodf.to_wkt()
    for id, row in enumerate(station_geodf.itertuples()):
        wkt = str(row.geometry)
        db.hset(f"station:{id}", "name", str(row.ifcid))
        db.hset(f"station:{id}", "geom", wkt) #zapis w postaci wkt pozwala na utw pola geoshape

def get_stations_id_from_redis(db:redis.Redis, wkt_polygon:str): #wkt poligon powiatu
    try:
        idx = create_geospatial_index(db)
    except Exception as e:
        print("Błąd podczas tworzenia indeksu geo", e)
        return
    
    params_dict = {"powiat": wkt_polygon}
    q = Query("@geom:[WITHIN $powiat]").dialect(3).return_field('name') #zapytanie do bazy o stacje w powiecie
    res = idx.search(q, query_params=params_dict)
    stations = []
    for document in res.docs:
        stations.append(document.name)
    
    return stations #lista z nazwami stacji do pozniejszego przetwarzania

#funkcje mongo
def find_pow(mongo_db, powiat:str):
    coll_name = "powiaty"
    coll = mongo_db[coll_name]
    result = coll.find_one({"name": powiat},
                           {"_id": 0, "geometry": 1})

    return result.get("geometry")

def liczenie(df):
    values = sorted(df[3].astype(float))

    percentile25 = np.percentile(values, 25)
    percentile75 = np.percentile(values, 75)

    values_cut = [v for v in values if percentile25 < v < percentile75]

    mean = np.mean(values)
    median = np.median(values)
    values_cut_mean = np.mean(values_cut)

    return mean, median, values_cut_mean

def find_date(df, target_date):
    date_col = pd.to_datetime(df.iloc[:, 2])
    date_only = date_col.dt.date
    target_date = pd.to_datetime(target_date)
    print(target_date)
    target_only_date = target_date.date()
    filtered_rows_by_date = df[date_only == target_only_date]

    return filtered_rows_by_date


def connect_mongo_db(uri:str, db_name:str):
    mongo_client = MongoClient(uri, server_api=ServerApi('1'))
    mongo_db = mongo_client[db_name]
    return mongo_db


def geostatistical_analysis(mongo_db, df, powiat, interval='daily'):

    # Filtracja danych dla wybranego powiatu
    powiat_geometry = find_pow(mongo_db, powiat)
    if not powiat_geometry:
        raise ValueError(f"Nie znaleziono powiatu: {powiat}")

    # Grupa stacji dla powiatu
    stations = get_stations_id_from_redis(redis_db, powiat_geometry)
    if not stations:
        raise ValueError(f"Brak stacji dla powiatu: {powiat}")

    df = df[df['Kod stacji'].isin(stations)]

    # Konwersja daty na typ datetime
    df['Data'] = pd.to_datetime(df['Data i godzina']).dt.date

    # Grupowanie danych według daty
    grouped = df.groupby('Data')['Wartość']

    # Obliczanie statystyk dla każdej daty
    stats = grouped.agg(['mean', 'median']).reset_index()
    stats.rename(columns={'mean': 'Średnia', 'median': 'Mediana'}, inplace=True)

    # Obliczanie zmian średniej i mediany w zadanych interwałach czasu
    stats['Zmiana Średniej'] = stats['Średnia'].diff()
    stats['Zmiana Median'] = stats['Mediana'].diff()

    return stats

from astral import LocationInfo
from astral.sun import sun

def is_day_or_night(timestamp, latitude, longitude):
    
    location = LocationInfo(latitude=latitude, longitude=longitude)
    s = sun(location.observer, date=timestamp.date())

    if s['sunrise'] <= timestamp <= s['sunset']:
        return "Dzień"
    else:
        return "Noc"


def get_station_coordinates_from_polygon(mongo_db, powiat):
    try:
        # Pobranie kolekcji z MongoDB
        collection = mongo_db['powiaty']

        # Wyszukanie dokumentu dla danego powiatu
        result = collection.find_one({"name": powiat}, {"geometry": 1, "_id": 0})

        if not result or "geometry" not in result:
            print(f"Nie znaleziono geometrii dla powiatu: {powiat}")
            return None

        geometry = result.get("geometry")

        if isinstance(geometry, str):
            # Parsowanie tekstu z geometrii
            match = re.search(r'POLYGON \(\((.*?)\)\)', geometry)
            if not match:
                print(f"Nie udało się znaleźć współrzędnych w geometrii powiatu '{powiat}'.")
                return None

            # Wyciąganie współrzędnych z tekstu
            coords_text = match.group(1)
            coords_pairs = coords_text.split(", ")

            # Pobranie pierwszego punktu
            first_point = coords_pairs[0]
            longitude, latitude = map(float, first_point.split())

            return latitude, longitude

        else:
            print(f"Nieobsługiwany format geometrii: {type(geometry)}")
            return None

    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania współrzędnych: {e}")
        return None

