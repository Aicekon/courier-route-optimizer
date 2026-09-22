# route_calculator.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pickle
import math
import numpy as np
from sklearn.cluster import KMeans
import re

class RouteCalculator:
    def __init__(self, city="Казань"):
        self.cache_file = "route_cache.pkl"
        self.city = city
        self.init_cache()
        self.init_driver()

    def init_cache(self):
        try:
            with open(self.cache_file, "rb") as f:
                self.cache = pickle.load(f)
        except (FileNotFoundError, EOFError):
            self.cache = {
                'coordinates': {},
                'routes': {},
                'clusters': {}
            }

    def init_driver(self):
        chrome_options = Options()
        #chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(options=chrome_options)

    def haversine_distance(self, coord1, coord2):
        """Рассчет расстояния между двумя точками по формуле гаверсинусов"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        R = 6371  # Радиус Земли в км

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def cluster_addresses(self, addresses_with_coords, num_clusters):
        """Создает кластеры по количеству курьеров"""
        if num_clusters <= 0 or not addresses_with_coords:
            return []

        # Используем KMeans для создания N кластеров
        coords = np.array([point[1] for point in addresses_with_coords])
        kmeans = KMeans(n_clusters=num_clusters, random_state=0).fit(coords)

        clusters = {}
        for label, point in zip(kmeans.labels_, addresses_with_coords):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(point)

        return list(clusters.values())

    def get_coordinates(self, address):
        """Универсальный парсер координат с обработкой разных форматов"""
        try:
            url = f"https://yandex.ru/maps/?text={self.city},{address}"
            self.driver.get(url)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                'div.toponym-card-title-view__coords-badge'))
            )

            coords_element = self.driver.find_element(By.CSS_SELECTOR,
                                                      'div.toponym-card-title-view__coords-badge')

            raw_coords = coords_element.text
            print(f"Raw coordinates: {raw_coords}")

            # Универсальный парсинг для разных форматов
            coords = self.parse_coordinates(raw_coords)

            if not coords or len(coords) != 2:
                raise ValueError(f"Некорректный формат координат: {raw_coords}")

            lat = round(coords[0], 6)
            lon = round(coords[1], 6)

            print(f"Parsed coordinates: {lat}, {lon}")
            return (lat, lon)

        except Exception as e:
            print(f"Ошибка при обработке координат для '{address}': {str(e)}")
            return None

    def parse_coordinates(self, raw_str):
        """Парсит координаты из любой строки Яндекса"""
        # Удаляем все символы кроме чисел, точек и запятых
        cleaned = re.sub(r'[^\d.,-]', '', raw_str)

        # Ищем все числа с плавающей точкой
        numbers = re.findall(r'-?\d+\.?\d*', cleaned)

        if len(numbers) >= 2:
            try:
                lat = float(numbers[0].replace(',', '.'))
                lon = float(numbers[1].replace(',', '.'))
                return (lat, lon)
            except:
                return None

        # Для форматов типа 55°48'08.0"N 49°10'42.7"E
        dms = re.findall(r'(\d+)°(\d+)\'([\d.]+)"([NSWE])', raw_str)
        if len(dms) == 2:
            lat = self.dms_to_decimal(dms[0])
            lon = self.dms_to_decimal(dms[1])
            return (lat, lon)

        return None

    def dms_to_decimal(self, dms):
        """Конвертирует градусы-минуты-секунды в десятичные градусы"""
        degrees, minutes, seconds, direction = dms
        decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
        if direction in ['S', 'W']:
            decimal *= -1
        return round(decimal, 6)

    def get_route_info(self, points):
        print("Типы координат в points:", [type(p[1]) for p in points])
    def get_route_info(self, points):
        """Получение информации о маршруте с кэшированием"""
        route_key = tuple( (p[0], tuple(p[1])) for p in points )
        if route_key in self.cache['routes']:
            return self.cache['routes'][route_key]

        try:
            coords_str = "~".join([f"{p[1][0]},{p[1][1]}" for p in points])
            url = f"https://yandex.ru/maps/?rtext={coords_str}&rtt=auto"
            self.driver.get(url)

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                '.auto-route-snippet-view__duration'))
            )

            time.sleep(2)

            time_element = self.driver.find_element(By.CSS_SELECTOR,
                                                    '.auto-route-snippet-view__duration')
            distance_element = self.driver.find_element(By.CSS_SELECTOR,
                                                        '.auto-route-snippet-view__distance')

            result = {
                'total_time': self.parse_time(time_element.text),
                'total_distance': self.parse_distance(distance_element.text)
            }

            self.cache['routes'][route_key] = result
            return result

        except Exception as e:
            print(f"Ошибка получения маршрута: {e}")
            return None

    def parse_time(self, time_str):
        """Парсинг времени маршрута в минуты"""
        parts = time_str.split()
        total = 0
        for i, part in enumerate(parts):
            if 'час' in part:
                total += int(parts[i - 1]) * 60
            elif 'мин' in part:
                total += int(parts[i - 1])
        return total

    def parse_distance(self, distance_str):
        """Парсинг расстояния в километры"""
        if 'км' in distance_str:
            return float(distance_str.replace(' км', '').replace(',', '.'))
        elif 'м' in distance_str:
            return float(distance_str.replace(' м', '')) / 1000
        return 0.0

    def optimize_routes(self, addresses_with_coords, couriers, start_point):
        num_couriers = len(couriers)
        clusters = self.cluster_addresses(addresses_with_coords, num_couriers)

        routes = {}
        for i, courier in enumerate(couriers):
            cluster = clusters[i] if i < len(clusters) else []
            optimized = self.optimize_cluster(start_point, cluster)

            routes[courier] = {
                'addresses': [p[0] for p in optimized['route']],
                'coordinates': [p[1] for p in optimized['route']],
                'total_time': optimized['total_time'] + len(cluster) * 5,  # +5 мин на точку
                'total_distance': optimized['total_distance']
            }

        return routes

    def init_cache(self):
        self.cache = {'coordinates': {}, 'routes': {}, 'clusters': {}}
    def optimize_cluster(self, start_point, cluster):
        """Оптимизация маршрута внутри кластера"""
        if not cluster:
            return {'route': [], 'total_time': 0, 'total_distance': 0}

        # Сортируем точки по удаленности от старта
        sorted_points = sorted(cluster, key=lambda x: self.haversine_distance(start_point, tuple(x[1])))


        # Парсим маршрут
        route_info = self.get_route_info([('start', start_point)] + sorted_points)

        return {
            'route': sorted_points,
            'total_time': route_info['total_time'] if route_info else 0,
            'total_distance': route_info['total_distance'] if route_info else 0
        }

    def sort_points(self, start, points):
        """Сортировка точек по алгоритму ближайшего соседа"""
        if not points:
            return []

        sorted_points = []
        remaining = points.copy()
        current_point = min(remaining, key=lambda x: self.haversine_distance(start, x[1]))
        remaining.remove(current_point)
        sorted_points.append(current_point)

        while remaining:
            next_point = min(remaining, key=lambda x: self.haversine_distance(sorted_points[-1][1], x[1]))
            remaining.remove(next_point)
            sorted_points.append(next_point)

        return sorted_points

    def save_cache(self):
        """Сохранение кэша в файл"""
        with open(self.cache_file, "wb") as f:
            pickle.dump(self.cache, f)

    def close(self):
        """Корректное закрытие драйвера"""
        self.save_cache()
        self.driver.quit()