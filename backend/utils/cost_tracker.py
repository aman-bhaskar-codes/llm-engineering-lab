class CostTracker:
    def __init__(self):
        self.total_cost = 0.0

    def add_cost(self, cost: float):
        self.total_cost += cost

    def get_total_cost(self) -> float:
        return self.total_cost
