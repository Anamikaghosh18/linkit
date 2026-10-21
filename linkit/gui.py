import tkinter as tk
from tkinter import ttk, messagebox
import threading
from .config import load_config, save_config, PORTAL_URL
from .credentials import get_credentials, clear_credentials, save_credentials
from .wifi import current_ssid
from .campus import connect_to_campus, discover_campus_networks, is_campus_ssid
from .portal import open_portal, authenticate
from .startup import install_startup
import time
import pystray
from PIL import Image


class ConnectWirelessGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("connect-wireless Setup")
        self.root.geometry("450x400")
        self.root.resizable(False, False)
        self.running = False
        self.icon = None
        self.setup_frame = None
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        # Check if already configured
        if self._stored_username():
            self.create_tray_icon()
            self.root.withdraw()
            self.start_background_service()
        else:
            self.create_setup_window()

    @staticmethod
    def _stored_username():
        """Read the saved username without letting credential-store errors crash startup."""
        try:
            username, _ = get_credentials()
            return username
        except Exception:
            return None

    def create_setup_window(self):
        # Remove any previously built setup UI so reopening settings does not
        # stack duplicate widgets on top of each other.
        for widget in list(self.root.winfo_children()):
            try:
                widget.destroy()
            except Exception:
                pass
        self.setup_frame = None

        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(header, text="linkit:connect-wireless", font=("Arial", 20, "bold"), 
                        bg="#2c3e50", fg="white")
        title.pack(pady=20)

        subtitle = tk.Label(header, text="Campus Wi-Fi Auto-Connect", font=("Arial", 10),
                           bg="#2c3e50", fg="#bdc3c7")
        subtitle.pack()

        # Content frame
        content = tk.Frame(self.root, padx=30, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        self.setup_frame = content

        # Info label: campus networks are found automatically
        tk.Label(
            content,
            text="Campus Wi-Fi networks are detected and joined automatically.",
            font=("Arial", 9),
            fg="#2c3e50",
            wraplength=380,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 15))

        # Username Field
        tk.Label(content, text="Portal Username:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        username_entry = ttk.Entry(content, textvariable=self.username_var, font=("Arial", 10))
        username_entry.pack(fill=tk.X, pady=(5, 15))

        # Password Field
        tk.Label(content, text="Portal Password:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        password_entry = ttk.Entry(content, textvariable=self.password_var, font=("Arial", 10), show="●")
        password_entry.pack(fill=tk.X, pady=(5, 15))

        # Buttons frame
        button_frame = tk.Frame(content)
        button_frame.pack(fill=tk.X, pady=20)

        # Reset Button
        reset_btn = ttk.Button(button_frame, text="Reset", command=self.reset_config)
        reset_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Continue Button
        continue_btn = ttk.Button(button_frame, text="Continue", command=self.save_and_start)
        continue_btn.pack(side=tk.RIGHT)

        # Info label
        info_label = tk.Label(content, text="Enter your campus Wi-Fi credentials to enable auto-connect.",
                             font=("Arial", 9), fg="#7f8c8d", wraplength=380)
        info_label.pack(side=tk.BOTTOM, pady=10)

        # Load existing config if available
        username = self._stored_username()
        if username:
            self.username_var.set(username)

        username_entry.focus()

    def reset_config(self):
        if messagebox.askyesno("Reset Configuration", 
                               "This will clear all saved credentials and settings. Continue?"):
            try:
                clear_credentials()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to clear credentials: {exc}")
                return
            cfg = load_config()
            save_config(cfg)
            self.username_var.set("")
            self.password_var.set("")
            messagebox.showinfo("Reset Complete", "Configuration has been reset.")

    def save_and_start(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username:
            messagebox.showerror("Error", "Please enter your portal username.")
            return
        if not password:
            messagebox.showerror("Error", "Please enter your portal password.")
            return

        try:
            # Save config
            cfg = load_config()
            cfg["portal_url"] = PORTAL_URL
            save_config(cfg)

            # Save credentials
            save_credentials(username, password)

            # Install startup
            install_startup()

            messagebox.showinfo("Setup Complete",
                              "connect-wireless is now configured and will start automatically with Windows.\n\n"
                              "The application will run in the background and auto-connect when the network is in range.")

            # Hide the setup window (the root owns the tray icon, so it must
            # stay alive) and start the background service.
            self.root.withdraw()
            self.create_tray_icon()
            self.start_background_service()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def create_tray_icon(self):
        if self.icon is not None:
            return
        # Create a simple icon (colored square)
        icon_image = Image.new('RGB', (64, 64), color='#3498db')
        self.icon = pystray.Icon("connect-wireless", icon_image, "connect-wireless")

        menu = pystray.Menu(
            pystray.MenuItem("Status", self.show_status),
            pystray.MenuItem("Open Settings", self.open_settings),
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.icon.menu = menu

        def run_icon():
            self.icon.run()

        threading.Thread(target=run_icon, daemon=True).start()

    def _on_tk_thread(self, func, *args):
        """Tk is not thread-safe: hop onto the main loop thread."""
        try:
            self.root.after(0, func, *args)
        except Exception:
            pass

    def show_status(self, icon, item):
        current = current_ssid() or "Not connected"
        status = "Running" if self.running else "Stopped"
        try:
            networks = discover_campus_networks()
        except Exception:
            networks = []
        if networks:
            names = ", ".join(network["ssid"] for network in networks)
            in_range = f"Campus networks in range: {names}"
        else:
            in_range = "Campus networks in range: none detected"
        self._on_tk_thread(
            messagebox.showinfo, "connect-wireless Status",
                          f"Current Connection: {current}\n"
                          f"{in_range}\n"
                          f"Status: {status}")

    def open_settings(self, icon, item):
        self._on_tk_thread(self._open_settings)

    def _open_settings(self):
        self.root.deiconify()
        self.create_setup_window()

    def quit_app(self, icon, item):
        self.running = False
        if self.icon:
            self.icon.stop()
        self._on_tk_thread(self._shutdown)

    def _shutdown(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def start_background_service(self):
        if self.running:
            return
        self.running = True
        
        def worker():
            cfg = load_config()

            last_portal_open = 0.0
            while self.running:
                try:
                    username, password = get_credentials()
                    if not username or not password:
                        time.sleep(30)
                        continue

                    current = current_ssid()
                    if current and is_campus_ssid(current):
                        ok, _message = authenticate(username, password, cfg.get("portal_url", PORTAL_URL))
                        if not ok:
                            now = time.time()
                            if cfg.get("open_portal_on_detect", True) and now - last_portal_open > 300:
                                open_portal(cfg.get("portal_url", PORTAL_URL))
                                last_portal_open = now
                    elif cfg.get("auto_connect", True):
                        connect_to_campus()

                    time.sleep(max(10, int(cfg.get("poll_seconds", 20))))
                except Exception:
                    time.sleep(30)

        threading.Thread(target=worker, daemon=True).start()

    def run(self):
        self.root.mainloop()

def main():
    app = ConnectWirelessGUI()
    app.run()

if __name__ == "__main__":
    main()
