import random
import threading
import time

import customtkinter as ctk
import requests

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class SenderUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Request Simulation")
        self.geometry("700x400")
        self.is_attacking = False
        self.target_ip = "127.0.0.1"

        # Split layout: Controls (left), Console (right)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.build_ui()

    def build_ui(self):
        # Left Panel: Controls
        control_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        control_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        self.req_label = ctk.CTkLabel(
            control_frame, text="Request Rate: 10 req/sec", font=("Consolas", 14)
        )
        self.req_label.pack(pady=(30, 10))
        self.req_slider = ctk.CTkSlider(
            control_frame, from_=1, to=100, command=self.update_labels
        )
        self.req_slider.set(10)
        self.req_slider.pack(pady=(0, 20), padx=20, fill="x")

        self.err_label = ctk.CTkLabel(
            control_frame, text="Intentional Error Rate: 5%", font=("Consolas", 14)
        )
        self.err_label.pack(pady=(10, 10))
        self.err_slider = ctk.CTkSlider(
            control_frame, from_=0, to=100, command=self.update_labels
        )
        self.err_slider.set(5)
        self.err_slider.pack(pady=(0, 30), padx=20, fill="x")

        self.attack_btn = ctk.CTkButton(
            control_frame,
            text="START TRAFFIC",
            font=("Consolas", 14, "bold"),
            fg_color="#8b0000",
            hover_color="#ff0000",
            command=self.toggle_attack,
        )
        self.attack_btn.pack(pady=10, ipadx=10, ipady=10)

        # Right Panel: Embedded Terminal
        terminal_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=10)
        terminal_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        self.console = ctk.CTkTextbox(
            terminal_frame,
            fg_color="transparent",
            text_color="#00ff00",
            font=("Consolas", 12),
        )
        self.console.pack(padx=10, pady=10, fill="both", expand=True)
        self.console.insert("0.0", "System Ready. Waiting for traffic parameters...\n")
        self.console.configure(state="disabled")

    def log_to_console(self, message):
        """Thread-safe GUI update for the embedded terminal."""
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def update_labels(self, _=None):
        req_val = int(self.req_slider.get())
        err_val = int(self.err_slider.get())
        self.req_label.configure(text=f"Request Rate: {req_val} req/sec")
        self.err_label.configure(text=f"Intentional Error Rate: {err_val}%")

    def toggle_attack(self):
        if not self.is_attacking:
            self.is_attacking = True
            self.attack_btn.configure(text="STOP TRAFFIC", fg_color="gray")
            self.log_to_console("[SYSTEM] Initiating traffic loop...")
            threading.Thread(target=self.traffic_loop, daemon=True).start()
        else:
            self.is_attacking = False
            self.attack_btn.configure(text="START TRAFFIC", fg_color="#8b0000")
            self.log_to_console("[SYSTEM] Traffic halted.")

    def send_single_request(self, status_payload):
        try:
            response = requests.post(
                f"http://{self.target_ip}:8000/traffic",
                json={"status": status_payload},
                timeout=0.5,
            )
            log_msg = f"[SENT] {status_payload.upper()} -> {self.target_ip} | Code: {response.status_code}"
            self.after(0, self.log_to_console, log_msg)
        except requests.exceptions.RequestException:
            err_msg = f"[FAILED] Target {self.target_ip}:8000 unreachable."
            self.after(0, self.log_to_console, err_msg)

    def traffic_loop(self):
        while self.is_attacking:
            req_per_sec = int(self.req_slider.get())
            err_chance = int(self.err_slider.get())
            status_payload = (
                "error" if random.randint(1, 100) <= err_chance else "success"
            )

            threading.Thread(
                target=self.send_single_request, args=(status_payload,), daemon=True
            ).start()
            time.sleep(1.0 / req_per_sec)


if __name__ == "__main__":
    app = SenderUI()
    app.mainloop()
