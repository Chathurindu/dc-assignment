class Node:

    def __init__(self, node_id, node_name, port, election=False, master=False):
        self.node_id = node_id
        self.node_name = node_name
        self.port = port
        self.election = election
        self.master = master


