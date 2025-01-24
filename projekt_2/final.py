import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import Entry, Listbox
import pandas as pd

import requests
import zipfile
import io

from astral import LocationInfo
from astral.sun import sun

import os
import datetime
import numpy as np

from funkcje import *

# Funkcja pobierająca listę dostępnych powiatów z MongoDB
def get_available_powiaty(db):
    powiaty = [record['name'] for record in db['powiaty'].find()]
    return powiaty

def download_and_extract_data(year, month):
    url = f"https://danepubliczne.imgw.pl/datastore/getfiledown/Arch/Telemetria/Meteo/{year}/Meteo_{year}-{str(month).zfill(2)}.zip"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Nie udało się pobrać danych dla {year}-{month}.")
    data_dir = f"./DaneMETEO/{year}_{str(month).zfill(2)}"
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(data_dir)
    return data_dir

def load_filtered_data(data_dir, data_type, stations):
    
    code = data_type_map[data_type]
    
    matching_file = None
    for file_name in os.listdir(data_dir):
        if code in file_name:
            matching_file = file_name
            break

    if not matching_file:
        raise FileNotFoundError(f"Nie znaleziono pliku dla kodu {code} w folderze {data_dir}.")

    file_path = os.path.join(data_dir, matching_file)
    
    try:
        df = pd.read_csv(file_path, sep=';', header=None, decimal=',')
    except Exception as e:
        raise ValueError(f"Nie udało się wczytać pliku {file_path}. Błąd: {e}")
    
    if df.shape[1] > 4:
        df = df.iloc[:, :4]
    elif df.shape[1] < 4:
        raise ValueError(f"Plik ma zbyt mało kolumn {df.shape[1]}).")

    df.columns = ['Kod stacji', 'Kod pliku', 'Data i godzina', 'Wartość']

    #print(f"Zawartość DataFrame po nadaniu nazw kolumn:\n{df.head()}")

    # Filtruj dane dla wybranych stacji
    stations = [int(station) for station in stations]  # Zamiana ID stacji na int
    df = df[df['Kod stacji'].isin(stations)]

    print(f"Debug: Zawartość DataFrame po filtrowaniu stacji ({stations}):\n{df.head()}")

    if df.empty:
        print("Debug: DataFrame jest pusty po filtrowaniu stacji.")
    return df

# Funkcja obliczająca statystyki
def calculate_statistics(df):
    if 'Wartość' not in df.columns:
        raise ValueError("Kolumna 'Wartość' nie istnieje w DataFrame.")

    stats = {
        'Min': df['Wartość'].min(),
        'Max': df['Wartość'].max(),
        'Średnia': df['Wartość'].mean(),
        'Suma': df['Wartość'].sum()
    }
    return stats

data_type_map = {
    "Temperatura powietrza (oficjalna)": "B00300S",
    "Temperatura gruntu (czujnik)": "B00305A",
    "Kierunek wiatru (czujnik)": "B00202A",
    "Średnia prędkość wiatru czujnik 10 minut": "B00702A",
    "Prędkość maksymalna (czujnik)": "B00703A",
    "Suma opadu 10 minutowego": "B00608S",
    "Suma opadu dobowego": "B00604S",
    "Suma opadu godzinowego": "B00606S",
    "Wilgotność względna powietrza (czujnik)": "B00802A",
    "Największy poryw w okresie 10min ze stacji Synoptycznej": "B00714A",
    "Zapas wody w śniegu (obserwator)": "B00910A"
    }


def run_interface(mongo_db, redis_db):

    # Funkcja do pobrania powiatów zawierających wpisane znaki
    def search_powiaty(prefix, mongo_db):
        powiaty = get_available_powiaty(mongo_db)
        return [powiat for powiat in powiaty if powiat.lower().startswith(prefix.lower())]

    # Funkcja aktualizująca liste powiatow
    def update_suggestions(event):
        prefix = powiat_entry.get()
        if len(prefix) > 0:
            suggestions = search_powiaty(prefix, mongo_db)
            suggestion_list.delete(0, tk.END)
            for suggestion in suggestions:
                suggestion_list.insert(tk.END, suggestion)

    # Funkcja wyboru powiatu 
    def select_powiat(event):
        selected_powiat = suggestion_list.get(suggestion_list.curselection())
        powiat_var.set(selected_powiat)
        suggestion_list.delete(0, tk.END)

    # def populate_powiaty():
    #     powiaty = get_available_powiaty(mongo_db)
    #     powiat_menu['menu'].delete(0, 'end')
    #     for powiat in sorted(powiaty):
    #         powiat_menu['menu'].add_command(label=powiat, command=tk._setit(powiat_var, powiat))

    def calculate_daily_and_weekly_intervals_fixed(df, specific_date, calculate_day_night=False, sunrise=None, sunset=None):
        
        # Konwersja kolumny "Data i godzina" na datetime
        df['Data i godzina'] = pd.to_datetime(df['Data i godzina'])
        df['Data'] = df['Data i godzina'].dt.date
        df['Czas'] = df['Data i godzina'].dt.time

        # Obliczanie statystyk dla konkretnego dnia
        specific_date = pd.to_datetime(specific_date).date()
        daily_data = df[df['Data'] == specific_date]
        if daily_data.empty:
            daily_stats = {"Średnia": None, "Mediana": None}
            if calculate_day_night:
                daily_stats.update({"Średnia dzień": None, "Mediana dzień": None, "Średnia noc": None, "Mediana noc": None})
        else:
            daily_stats = {
                "Średnia": daily_data['Wartość'].mean(),
                "Mediana": daily_data['Wartość'].median()
            }

            # Podział na dzień i noc, jeśli wymagane
            if calculate_day_night and sunrise and sunset:
                day_data = daily_data[(daily_data['Czas'] >= sunrise) & (daily_data['Czas'] <= sunset)]
                night_data = daily_data[(daily_data['Czas'] < sunrise) | (daily_data['Czas'] > sunset)]

                daily_stats.update({
                    "Średnia dzień": day_data['Wartość'].mean() if not day_data.empty else None,
                    "Mediana dzień": day_data['Wartość'].median() if not day_data.empty else None,
                    "Średnia noc": night_data['Wartość'].mean() if not night_data.empty else None,
                    "Mediana noc": night_data['Wartość'].median() if not night_data.empty else None,
                })

        # Dodanie kolumny "Dzień miesiąca" na podstawie kolumny datetime
        df['Dzień miesiąca'] = df['Data i godzina'].dt.day

        # Filtracja danych dla każdego przedziału tygodniowego
        intervals = {
            "1-7": df[(df['Dzień miesiąca'] >= 1) & (df['Dzień miesiąca'] <= 7)],
            "8-14": df[(df['Dzień miesiąca'] >= 8) & (df['Dzień miesiąca'] <= 14)],
            "15-21": df[(df['Dzień miesiąca'] >= 15) & (df['Dzień miesiąca'] <= 21)],
            "22-31": df[(df['Dzień miesiąca'] >= 22) & (df['Dzień miesiąca'] <= 31)],
        }

        # Obliczanie średniej i mediany dla każdego interwału
        interval_stats = {}
        for interval, data in intervals.items():
            if not data.empty:
                mean_value = data['Wartość'].mean()
                median_value = data['Wartość'].median()
                interval_stats[interval] = {"Średnia": mean_value, "Mediana": median_value}
            else:
                # Jeśli brak danych w interwale brak danych
                interval_stats[interval] = {"Średnia": "Brak danych", "Mediana": "Brak danych"}

        return daily_stats, interval_stats


    def run_analysis():
        try:
            powiat = powiat_var.get()
            date = date_entry.get()
            data_type = data_type_var.get()
            print(data_type)
            calculate_day_night = day_night_var.get()

            station_coords = get_station_coordinates_from_polygon(mongo_db, powiat) if calculate_day_night else None

            if station_coords:
                print("ok")
            else:
                if calculate_day_night:
                    messagebox.showerror("Błąd", "Nie udało się pobrać współrzędnych punktu powiatu.")
                    return
                
            powiat_wkt = find_pow(mongo_db, powiat)

            stations = get_stations_id_from_redis(redis_db, powiat_wkt)

            if not stations:
                messagebox.showinfo("Wynik", "Brak stacji w wybranym powiecie.")
                return

            # Pobranie danych dla określonego miesiąca
            year, month = map(int, date.split("-")[:2])
            data_dir = download_and_extract_data(year, month)

            # Wczytanie danych dla całego miesiąca
            df_full = load_filtered_data(data_dir, data_type, stations)

            if df_full.empty:
                messagebox.showinfo("Wynik", "Brak danych spełniających kryteria.")
                return

            # Obliczenie godzin wschodu i zachodu słońca (jeśli zaznaczony checkbox)
            sunrise, sunset = None, None
            if calculate_day_night and station_coords:
                location = LocationInfo(name=powiat, region="Poland", timezone="Europe/Warsaw", latitude=station_coords[0], longitude=station_coords[1])
                sun_times = sun(location.observer, date=pd.to_datetime(date))
                sunrise = sun_times["sunrise"].time()
                sunset = sun_times["sunset"].time()

                print(f"Debug: Godziny wschodu i zachodu słońca dla {date}: Wschód - {sunrise}, Zachód - {sunset}")

            # Obliczenie statystyk dla wybranego dnia i interwałów tygodniowych
            daily_stats, interval_stats = calculate_daily_and_weekly_intervals_fixed(
                df_full, 
                date, 
                calculate_day_night=calculate_day_night,  
                sunrise=sunrise, 
                sunset=sunset
            )

            # Formatowanie wyników
            result = f"Statystyki dla danych: {data_type}\n"
            result += f"Powiat: {powiat}\n\n"
            result += f"Średnia wartość (dla {date}): {daily_stats['Średnia']:.2f}\n" if daily_stats["Średnia"] is not None else "Brak danych dla wybranego dnia.\n"
            result += f"Mediana wartośći (dla {date}): {daily_stats['Mediana']:.2f}\n\n" if daily_stats["Mediana"] is not None else ""

            if calculate_day_night:
                result += f"Średnia (dzień): {daily_stats['Średnia dzień']:.2f}\n" if daily_stats.get("Średnia dzień") else ""
                result += f"Mediana (dzień): {daily_stats['Mediana dzień']:.2f}\n" if daily_stats.get("Mediana dzień") else ""
                result += f"Średnia (noc): {daily_stats['Średnia noc']:.2f}\n" if daily_stats.get("Średnia noc") else ""
                result += f"Mediana (noc): {daily_stats['Mediana noc']:.2f}\n\n" if daily_stats.get("Mediana noc") else ""

            result += "Średnia i mediana dla interwałów tygodniowych:\n"
            for interval, stats in interval_stats.items():
                if stats["Średnia"] is not None:
                    result += f"{interval} - Średnia: {stats['Średnia']:.2f}, Mediana: {stats['Mediana']:.2f}\n"
                else:
                    result += f"{interval} - Brak danych\n"

            print(f"Debug: Wynik analizy:\n{result}")

            # Wyświetlenie wyników
            messagebox.showinfo("Statystyki", result)

        except Exception as e:
            print(f"Debug: Wystąpił błąd: {e}")
            messagebox.showerror("Błąd", str(e))


    root = tk.Tk()
    root.title("Analiza danych meteo")

    tk.Label(root, text="Powiat:").grid(row=0, column=0)
    powiat_var = tk.StringVar()
    powiat_entry = Entry(root, textvariable=powiat_var)
    powiat_entry.grid(row=0, column=1)
    suggestion_list = Listbox(root, height=5, width=30)
    suggestion_list.grid(row=1, column=1, sticky="ew")

    powiat_entry.bind("<KeyRelease>", update_suggestions)
    suggestion_list.bind("<Double-1>", select_powiat)

    tk.Label(root, text="Data (YYYY-MM-DD):").grid(row=2, column=0)
    date_entry = tk.Entry(root)
    date_entry.grid(row=2, column=1)

    tk.Label(root, text="Rodzaj danych:").grid(row=3, column=0)
    data_type_var = tk.StringVar(value="Temperatura powietrza (oficjalna)")
    tk.OptionMenu(root, data_type_var, *data_type_map.keys()).grid(row=3, column=1)

    day_night_var = tk.BooleanVar()
    tk.Checkbutton(root, text="Uwzględnij dzień i noc", variable=day_night_var).grid(row=4, column=0, columnspan=2)

    tk.Button(root, text="Analizuj", command=run_analysis).grid(row=5, column=0, columnspan=2)

    root.mainloop()


if __name__ == "__main__":
    #poł mongo
    mongo_uri = "..."
    mongo_db = connect_mongo_db(mongo_uri, "...")

    #połączenie do redisa
    redis_db = connect_redis_db('...',
                          '...' ,'...')
    
    #lepieej raz polaczyc sie do baz niz za kazdym razem przy odpalaniu funkcji run analysis
    run_interface(mongo_db, redis_db)