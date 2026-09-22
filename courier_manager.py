# courier_manager.py
class CourierManager:
    def __init__(self):
        self.couriers = []

    def add_courier(self, name):
        self.couriers.append(name)

    def get_couriers(self):
        return self.couriers.copy()