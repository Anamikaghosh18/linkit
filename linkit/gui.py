import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
from .config import load_config, save_config, APP_DIR, CONFIG_PATH, PORTAL_URL
from .credentials import prompt_and_save, get_credentials, clear_credentials
from .wifi import current_ssid, visible_ssids, is_visible, connect_using_saved_profile
from .portal import open_portal, authenticate
from .startup import install_startup, uninstall_startup
import time
import pystray
from PIL import Image
import queue

class LinkWirelessGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("linkit Setup")
        self.root.geometry("450x400")
        self.root.resizable(False, False)
        self.running = False
        self.worker_queue = queue.Queue()
        self.icon = None

        # Check if already configured
        cfg = load_config()
        if cfg.get("ssid") and get_credentials()[0]:
            self.create_tray_icon()
            self.root.withdraw()
            self.start_background_service()
        else:
            self.create_setup_window()

    def create_setup_window(self):
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(header, text="linkit", font=("Arial", 24, "bold"), 
                        bg="#2c3e50", fg="white")
        title.pack(pady=20)

        subtitle = tk.Label(header, text="Campus Wi-Fi Auto-Connect", font=("Arial", 10),
                           bg="#2c3e50", fg="#bdc3c7")
        subtitle.pack()

        # Content frame
        content = tk.Frame(self.root, padx=30, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # SSID Field
        tk.Label(content, text="Wi-Fi Network Name (SSID):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.ssid_var = tk.StringVar()
        ssid_entry = ttk.Entry(content, textvariable=self.ssid_var, font=("Arial", 10))
        ssid_entry.pack(fill=tk.X, pady=(5, 15))
        ssid_entry.focus()

        # Username Field
        tk.Label(content, text="Portal Username:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(content, textvariable=self.username_var, font=("Arial", 10))
        username_entry.pack(fill=tk.X, pady=(5, 15))

        # Password Field
        tk.Label(content, text="Portal Password:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.password_var = tk.StringVar()
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
        cfg = load_config()
        if cfg.get("ssid"):
            self.ssid_var.set(cfg["ssid"])
        try:
            username, _ = get_credentials()
            if username:
                self.username_var.set(username)
        except:
            pass

    def reset_config(self):
        if messagebox.askyesno("Reset Configuration", 
                               "This will clear all saved credentials and settings. Continue?"):
            clear_credentials()
            cfg = load_config()
            cfg["ssid"] = ""
            save_config(cfg)
            self.ssid_var.set("")
            self.username_var.set("")
            self.password_var.set("")
            messagebox.showinfo("Reset Complete", "Configuration has been reset.")

    def save_and_start(self):
        ssid = self.ssid_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not ssid:
            messagebox.showerror("Error", "Please enter the Wi-Fi network name (SSID).")
            return
        if not username:
            messagebox.showerror("Error", "Please enter your portal username.")
            return
        if not password:
            messagebox.showerror("Error", "Please enter your portal password.")
            return

        try:
            # Save config
            cfg = load_config()
            cfg["ssid"] = ssid
            cfg["portal_url"] = PORTAL_URL
            save_config(cfg)

            # Save credentials
            from .credentials import save_credentials
            save_credentials(username, password)

            # Install startup
            install_startup()

            messagebox.showinfo("Setup Complete", 
                              "linkit is now configured and will start automatically with Windows.\n\n"
                              "The application will run in the background and auto-connect when the network is in range.")

            # Close setup window and start background service
            self.root.destroy()
            self.create_tray_icon()
            self.start_background_service()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def create_tray_icon(self):
        # Create a simple icon (colored square)
        icon_image = Image.new('RGB', (64, 64), color='#3498db')
        self.icon = pystray.Icon("linkit", icon_image, "linkit")

        menu = pystray.Menu(
            pystray.MenuItem("Status", self.show_status),
            pystray.MenuItem("Open Settings", self.open_settings),
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.icon.menu = menu

        def run_icon():
            self.icon.run()

        threading.Thread(target=run_icon, daemon=True).start()

    def show_status(self, icon, item):
        cfg = load_config()
        ssid = cfg.get("ssid", "Not configured")
        current = current_ssid() or "Not connected"
        messagebox.showinfo("linkit Status", 
                          f"Target Network: {ssid}\n"
                          f"Current Connection: {current}\n"
                          f"Status: {'Running' if self.running else 'Stopped'}")

    def open_settings(self, icon, item):
        self.root.deiconify()
        self.create_setup_window()

    def quit_app(self, icon, item):
        self.running = False
        if self.icon:
            self.icon.stop()
        sys.exit(0)

    def start_background_service(self):
        self.running = True
        
        def worker():
            cfg = load_config()
            ssid = cfg.get("ssid", "").strip()
            if not ssid:
                return

            last_portal_open = 0.0
            while self.running:
                try:
                    username, password = get_credentials()
                    if not username or not password:
                        time.sleep(30)
                        continue

                    current = current_ssid()
                    if current and current.casefold() == ssid.casefold():
                        ok, message = authenticate(username, password, cfg.get("portal_url", PORTAL_URL))
                        if not ok:
                            now = time.time()
                            if cfg.get("open_portal_on_detect", True) and now - last_portal_open > 300:
                                open_portal(cfg.get("portal_url", PORTAL_URL))
                                last_portal_open = now
                    elif cfg.get("auto_connect", True) and is_visible(ssid):
                        connect_using_saved_profile(ssid)
                    
                    time.sleep(max(10, int(cfg.get("poll_seconds", 20))))
                except Exception as exc:
                    time.sleep(30)

        threading.Thread(target=worker, daemon=True).start()

    def run(self):
        self.root.mainloop()

def main():
    app = LinkWirelessGUI()
    app.run()

if __name__ == "__main__":
    main()
