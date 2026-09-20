import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class ThreatFuzzyEngine:
    def __init__(self):
        # 1. Define the Universe of Discourse (The X-Axis ranges)
        # Request Rate: 0 to 100 requests per second
        self.req_rate = ctrl.Antecedent(np.arange(0, 101, 1), "request_rate")
        # Error Rate: 0 to 100 percentage
        self.err_rate = ctrl.Antecedent(np.arange(0, 101, 1), "error_rate")
        # Final Threat Level: 0 to 100 percentage
        self.threat = ctrl.Consequent(np.arange(0, 101, 1), "threat_level")

        # 2. Define Triangular Membership Functions (The actual graph shapes)
        # Request Rate categories (Low, Medium, High)
        self.req_rate["low"] = fuzz.trimf(self.req_rate.universe, [0, 0, 20])
        self.req_rate["medium"] = fuzz.trimf(self.req_rate.universe, [10, 30, 60])
        self.req_rate["high"] = fuzz.trimf(self.req_rate.universe, [40, 100, 100])

        # Error Rate categories
        self.err_rate["low"] = fuzz.trimf(self.err_rate.universe, [0, 0, 30])
        self.err_rate["medium"] = fuzz.trimf(self.err_rate.universe, [10, 40, 70])
        self.err_rate["high"] = fuzz.trimf(self.err_rate.universe, [50, 100, 100])

        # Threat Level categories
        self.threat["low"] = fuzz.trimf(self.threat.universe, [0, 0, 40])
        self.threat["moderate"] = fuzz.trimf(self.threat.universe, [20, 50, 80])
        self.threat["severe"] = fuzz.trimf(self.threat.universe, [60, 100, 100])

        # 3. Define the Mamdani Rule Matrix
        # Note how High Request Rate + Low Error Rate only yields a 'moderate' threat (Viral Spike),
        # but High Request Rate + High Error Rate yields 'severe' (Brute Force).
        rule1 = ctrl.Rule(
            self.req_rate["low"] & self.err_rate["low"], self.threat["low"]
        )
        rule2 = ctrl.Rule(
            self.req_rate["low"] & self.err_rate["medium"], self.threat["low"]
        )
        rule3 = ctrl.Rule(
            self.req_rate["low"] & self.err_rate["high"], self.threat["moderate"]
        )

        rule4 = ctrl.Rule(
            self.req_rate["medium"] & self.err_rate["low"], self.threat["low"]
        )
        rule5 = ctrl.Rule(
            self.req_rate["medium"] & self.err_rate["medium"], self.threat["moderate"]
        )
        rule6 = ctrl.Rule(
            self.req_rate["medium"] & self.err_rate["high"], self.threat["severe"]
        )

        rule7 = ctrl.Rule(
            self.req_rate["high"] & self.err_rate["low"], self.threat["moderate"]
        )
        rule8 = ctrl.Rule(
            self.req_rate["high"] & self.err_rate["medium"], self.threat["severe"]
        )
        rule9 = ctrl.Rule(
            self.req_rate["high"] & self.err_rate["high"], self.threat["severe"]
        )

        # 4. Build and Simulate the Control System
        self.threat_ctrl = ctrl.ControlSystem(
            [rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9]
        )
        self.threat_sim = ctrl.ControlSystemSimulation(self.threat_ctrl)

    def compute_threat(self, current_req_rate, current_err_rate):
        """Passes live API metrics into the engine and returns a defuzzified score."""
        self.threat_sim.input["request_rate"] = current_req_rate
        self.threat_sim.input["error_rate"] = current_err_rate

        self.threat_sim.compute()
        return self.threat_sim.output["threat_level"]


# Quick terminal test to verify math without the GUI
if __name__ == "__main__":
    engine = ThreatFuzzyEngine()
    print(
        f"Viral Spike Test (90 req/s, 5% error): {engine.compute_threat(90, 5):.2f}% Threat"
    )
    print(
        f"Brute Force Test (90 req/s, 85% error): {engine.compute_threat(90, 85):.2f}% Threat"
    )
