# address_manager.py
class AddressManager:
    def __init__(self):
        self.addresses = []

    def add_address(self, address):
        self.addresses.append(address)

    def get_addresses(self):
        return self.addresses.copy()