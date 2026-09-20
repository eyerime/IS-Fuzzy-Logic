import threading
import time

import customtkinter as ctk
import matplotlib.pyplot as plt
import uvicorn
from api_server import app, engine, traffic_log
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class ReceiverUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fuzzy Logic Engine")
        self.geometry("1100x650")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.ui_update_task = None

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        # Left Panel: Text Statistics
        self.stats_frame = ctk.CTkFrame(
            self,
            fg_color="#181818",
            corner_radius=10,
            border_width=1,
            border_color="#333333",
        )
        self.stats_frame.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="nsew")

        self.lbl_req = ctk.CTkLabel(
            self.stats_frame, text="Req Rate: 0.0/s", font=("Consolas", 18)
        )
        self.lbl_req.pack(pady=(40, 20))

        self.lbl_err = ctk.CTkLabel(
            self.stats_frame, text="Err Rate: 0.0%", font=("Consolas", 18)
        )
        self.lbl_err.pack(pady=20)

        self.lbl_threat = ctk.CTkLabel(
            self.stats_frame,
            text="Threat Level\n0.0%",
            font=("Consolas", 26, "bold"),
            text_color="#00ff00",
        )
        self.lbl_threat.pack(pady=40)

        # Right Panel: Tabbed View for Graphs
        self.tabview = ctk.CTkTabview(
            self, fg_color="#181818", segmented_button_selected_color="#004488"
        )
        self.tabview.grid(row=0, column=1, padx=(5, 15), pady=10, sticky="nsew")

        self.tab_live = self.tabview.add("Live Threat Time-Series")
        self.tab_mamdani = self.tabview.add("Fuzzy Membership (Triangles)")

        # Embed Live Graph in Tab 1
        self.fig, self.ax = plt.subplots(figsize=(7, 5), facecolor="#181818")
        self.ax.set_facecolor("#121212")
        self.ax.tick_params(colors="white")
        for spine in self.ax.spines.values():
            spine.set_color("#333333")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_live)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.threat_history = [0] * 50

        # Embed Fuzzy Triangles in Tab 2
        self.fig_fuzzy, (self.ax_req, self.ax_err, self.ax_thr) = plt.subplots(
            3, 1, figsize=(7, 6), facecolor="#181818"
        )
        self.fig_fuzzy.tight_layout(pad=3.0)

        self.canvas_fuzzy = FigureCanvasTkAgg(self.fig_fuzzy, master=self.tab_mamdani)
        self.canvas_fuzzy.get_tk_widget().pack(fill="both", expand=True)

        self.api_thread = threading.Thread(target=self.run_server, daemon=True)
        self.api_thread.start()

        self.update_ui()

    def run_server(self):
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

    def update_ui(self):
        total_requests = len(traffic_log)
        req_per_sec = total_requests / 10.0
        error_count = sum(1 for req in traffic_log if req[1] == "error")
        err_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        capped_req = min(req_per_sec, 100)

        threat_score = engine.compute_threat(capped_req, err_rate)

        # Determine strict color tiers
        line_color = (
            "#ff4444"
            if threat_score > 75
            else ("#ffaa00" if threat_score > 40 else "#00ff00")
        )

        self.lbl_req.configure(text=f"Req Rate: {req_per_sec:.1f}/s")
        self.lbl_err.configure(text=f"Err Rate: {err_rate:.1f}%")
        self.lbl_threat.configure(
            text=f"Threat Level\n{threat_score:.1f}%", text_color=line_color
        )

        # Update Time-Series
        self.threat_history.append(threat_score)
        self.threat_history.pop(0)

        self.ax.clear()
        self.ax.plot(self.threat_history, color=line_color, linewidth=2)
        self.ax.set_ylim(0, 100)
        self.ax.set_title("Live Threat Level", color="white")
        self.ax.set_facecolor("#121212")
        self.canvas.draw_idle()

        # Update Fuzzy Visualization
        for ax in (self.ax_req, self.ax_err, self.ax_thr):
            ax.clear()
            ax.set_facecolor("#121212")
            ax.tick_params(colors="white")
            for spine in ax.spines.values():
                spine.set_color("#333333")

        self.ax_req.set_title("Request Rate Context", color="white")
        for label, term in engine.req_rate.terms.items():
            self.ax_req.plot(engine.req_rate.universe, term.mf, label=label)
        self.ax_req.axvline(x=capped_req, color="cyan", linestyle="--", linewidth=2)

        self.ax_err.set_title("Error Rate Context", color="white")
        for label, term in engine.err_rate.terms.items():
            self.ax_err.plot(engine.err_rate.universe, term.mf, label=label)
        self.ax_err.axvline(x=err_rate, color="cyan", linestyle="--", linewidth=2)

        self.ax_thr.set_title("Defuzzification Output", color="white")
        for label, term in engine.threat.terms.items():
            self.ax_thr.plot(engine.threat.universe, term.mf, label=label, alpha=0.4)
        self.ax_thr.axvline(
            x=threat_score,
            color=line_color,
            linewidth=3,
            label=f"Centroid: {threat_score:.1f}%",
        )

        for ax in (self.ax_req, self.ax_err, self.ax_thr):
            ax.legend(
                loc="upper right",
                fontsize="small",
                facecolor="#181818",
                labelcolor="white",
            )

        self.canvas_fuzzy.draw_idle()
        self.after(500, self.update_ui)

    def on_closing(self):
        """Safely cancels pending GUI loops and kills the application."""
        if self.ui_update_task is not None:
            self.after_cancel(self.ui_update_task)

        self.quit()
        self.destroy()


if __name__ == "__main__":
    app_ui = ReceiverUI()
    app_ui.mainloop()
