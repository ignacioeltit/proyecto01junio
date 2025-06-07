class EmuladorOBD:
    def __init__(self):
        self.connected = False
        
    def connect(self):
        self.connected = True
        return True
