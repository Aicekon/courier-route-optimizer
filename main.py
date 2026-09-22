# main.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Toplevel
import json
import threading
import time
from route_calculator import RouteCalculator


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Оптимизатор маршрутов")
        self.geometry("1200x900")

        # Стилизация
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure(bg='#F0F8FF')
        self.style.configure('Accent.TButton',
                             foreground='white',
                             background='#1E90FF',
                             font=('Arial', 12, 'bold'),
                             padding=10)

        # Настройка сетки
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=3)

        # Верхняя панель управления
        self.control_frame = ttk.Frame(self)
        self.control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        ttk.Button(self.control_frame, text="⚙ Настройки", command=self.show_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="🧹 Очистить кэш", command=self.clear_cache).pack(side=tk.LEFT, padx=5)

        # Блоки адресов и курьеров
        self.content_frame = ttk.Frame(self)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Адреса (слева)
        self.address_frame = ttk.LabelFrame(self.content_frame, text="📬 Адреса")
        self.address_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Курьеры (справа)
        self.courier_frame = ttk.LabelFrame(self.content_frame, text="🚚 Курьеры")
        self.courier_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Результаты и кнопка расчета
        self.results_frame = ttk.LabelFrame(self, text="📊 Результаты")
        self.results_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        # Кнопка расчета внутри блока результатов
        self.calc_button = ttk.Button(
            self.results_frame,
            text="🚀 Начать расчет",
            style='Accent.TButton',
            command=self.start_calculation_thread
        )
        self.calc_button.pack(side=tk.BOTTOM, pady=10, anchor=tk.CENTER)

        # Инициализация компонентов
        self.init_address_components()
        self.init_courier_components()
        self.init_results_components()

        self.route_calculator = None
        self.running = False
        self.settings = {
            'start_point': (55.826402, 49.118985),
            'city': 'Казань'
        }

        self.load_data()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def init_address_components(self):
        # Поле ввода адреса
        self.address_entry = ttk.Entry(self.address_frame)
        self.address_entry.pack(fill=tk.X, padx=5, pady=5)

        # Кнопки управления
        btn_frame = ttk.Frame(self.address_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Добавить", command=self.add_address).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.remove_address).pack(side=tk.LEFT)

        # Список адресов с прокруткой
        self.address_listbox = tk.Listbox(self.address_frame, height=15, font=('Arial', 10))
        scroll = ttk.Scrollbar(self.address_frame, orient="vertical", command=self.address_listbox.yview)
        self.address_listbox.configure(yscrollcommand=scroll.set)
        self.address_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def init_courier_components(self):
        # Кнопки управления
        btn_frame = ttk.Frame(self.courier_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Добавить", command=self.add_courier).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.remove_courier).pack(side=tk.LEFT)

        # Список курьеров с прокруткой
        self.courier_listbox = tk.Listbox(self.courier_frame, height=15, font=('Arial', 10))
        scroll = ttk.Scrollbar(self.courier_frame, orient="vertical", command=self.courier_listbox.yview)
        self.courier_listbox.configure(yscrollcommand=scroll.set)
        self.courier_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.courier_listbox.bind('<Double-Button-1>', self.rename_courier)

    def init_results_components(self):
        # Область результатов с прокруткой
        self.results_canvas = tk.Canvas(self.results_frame, bg='#F0F8FF')
        self.results_scroll = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_canvas.yview)
        self.results_inner_frame = ttk.Frame(self.results_canvas)

        self.results_inner_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )
        self.results_canvas.create_window((0, 0), window=self.results_inner_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=self.results_scroll.set)

        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def add_address(self):
        address = self.address_entry.get().strip()
        if address:
            self.address_listbox.insert(tk.END, address)
            self.address_entry.delete(0, tk.END)

    def remove_address(self):
        selected = self.address_listbox.curselection()
        if selected:
            self.address_listbox.delete(selected[0])

    def add_courier(self):
        courier_id = f"Курьер {self.courier_listbox.size() + 1}"
        self.courier_listbox.insert(tk.END, courier_id)

    def remove_courier(self):
        selected = self.courier_listbox.curselection()
        if selected:
            self.courier_listbox.delete(selected[0])

    def rename_courier(self, event):
        selected = self.courier_listbox.curselection()
        if selected:
            new_name = simpledialog.askstring("Переименование", "Введите новое имя курьера:", parent=self)
            if new_name:
                self.courier_listbox.delete(selected[0])
                self.courier_listbox.insert(selected[0], new_name)

    def show_settings(self):
        settings_win = Toplevel(self)
        settings_win.title("⚙ Настройки")
        settings_win.geometry("400x200")

        ttk.Label(settings_win, text="Начальные координаты (lat,lon):").pack(pady=5)
        start_var = tk.StringVar(value=f"{self.settings['start_point'][0]}, {self.settings['start_point'][1]}")
        ttk.Entry(settings_win, textvariable=start_var, width=35).pack()

        ttk.Label(settings_win, text="Город по умолчанию:").pack(pady=5)
        city_var = tk.StringVar(value=self.settings['city'])
        ttk.Entry(settings_win, textvariable=city_var).pack()

        ttk.Button(settings_win, text="Сохранить",
                   command=lambda: self.save_settings(start_var.get(), city_var.get())).pack(pady=15)

    def save_settings(self, start_str, city):
        try:
            lat, lon = map(float, start_str.replace(' ', '').split(','))
            self.settings['start_point'] = (lat, lon)
            self.settings['city'] = city.strip()
            messagebox.showinfo("Сохранено", "Настройки успешно обновлены!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Некорректные данные: {str(e)}")

    def clear_cache(self):
        try:
            self.route_calculator = RouteCalculator()
            self.route_calculator.clear_cache()
            messagebox.showinfo("Кэш очищен", "Все кэшированные данные удалены")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def start_calculation_thread(self):
        if self.running:
            return
        self.running = True
        self.calc_button.config(state=tk.DISABLED)
        threading.Thread(target=self.start_calculation).start()

    def start_calculation(self):
        try:
            addresses = self.address_listbox.get(0, tk.END)
            couriers = self.courier_listbox.get(0, tk.END)

            if not addresses or not couriers:
                raise ValueError("Добавьте адреса и курьеров")

            self.route_calculator = RouteCalculator(city=self.settings['city'])

            addresses_with_coords = []
            for idx, address in enumerate(addresses, 1):
                coord = self.route_calculator.get_coordinates(address)
                if coord:
                    addresses_with_coords.append((address, tuple(coord)))
                time.sleep(0.5)

            optimized_routes = self.route_calculator.optimize_routes(
                addresses_with_coords,
                couriers,
                self.settings['start_point']
            )

            self.display_results(optimized_routes)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            if self.route_calculator:
                self.route_calculator.close()
            self.running = False
            self.calc_button.config(state=tk.NORMAL)

    def display_results(self, routes):
        # Очистка предыдущих результатов
        for widget in self.results_inner_frame.winfo_children():
            widget.destroy()

        if not routes:
            ttk.Label(self.results_inner_frame, text="Нет данных для отображения").pack(pady=10)
            return

        # Добавление новых результатов
        for courier, data in routes.items():
            frame = ttk.LabelFrame(self.results_inner_frame, text=f"📦 {courier}")
            frame.pack(fill=tk.X, pady=5, padx=10)

            ttk.Label(frame, text=f"⏱ Время: {data['total_time']} мин").pack(anchor='w')
            ttk.Label(frame, text=f"📏 Расстояние: {data['total_distance']:.2f} км").pack(anchor='w')

            for i, address in enumerate(data['addresses'], 1):
                ttk.Label(frame, text=f"{i}. {address}").pack(anchor='w', padx=20)

    def load_data(self):
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.settings.update(data.get('settings', {}))
                for addr in data.get('addresses', []):
                    self.address_listbox.insert(tk.END, addr)
                for courier in data.get('couriers', []):
                    self.courier_listbox.insert(tk.END, courier)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        data = {
            'settings': self.settings,
            'addresses': self.address_listbox.get(0, tk.END),
            'couriers': self.courier_listbox.get(0, tk.END)
        }
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def on_closing(self):
        self.save_data()
        if self.route_calculator:
            self.route_calculator.close()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()