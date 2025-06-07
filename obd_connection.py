class OBDConnection:
    def __init__(self):
        self.connected = False
        
    def connect(self):
        self.connected = True
        return True
        
    def disconnect(self):
        self.connected = False
