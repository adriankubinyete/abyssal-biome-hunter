import os
import sys
import time
import asyncio
import logging
import configparser
import tkinter as tk
from functools import partial, partialmethod # for log shenanigans
from tkinter import ttk
from utils.log_utils import file_handler, console_handler
from utils.roblox_application import RobloxApplication

logger = logging.getLogger('abyssal')
logger.setLevel(logging.TEST)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class Application:
    def __init__(self):
        self.roblox_app = RobloxApplication()
        self.roblox_app.on_biome_change(self.handle_biome_change)
        self.qty_biome_changes = 0
        
        # Define o caminho para o config.ini
        if getattr(sys, 'frozen', False):
            # Se estiver sendo executado como um executável, o arquivo estará no mesmo diretório do .exe
            config_path = os.path.join(os.path.dirname(sys.executable), 'config.ini')
        else:
            # Durante o desenvolvimento, o arquivo estará no mesmo diretório do script Python
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
        
        # Carrega o arquivo de configuração
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Setting up the tkinter interface
        self.window = tk.Tk()
        self.window.title("Abyssal Biome Hunter")
        self.window.geometry("650x250")  # Fixed window size (width x height)
        self.window.resizable(False, False)  # Prevent resizing of window
        
        # Frame to hold all content
        main_frame = tk.Frame(self.window, padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.config(bg="#f0f0f0")  # Light gray background for the main frame
        
        # Configure the window to expand the main frame
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        
        # Webhook URL field
        webhook_label = ttk.Label(main_frame, text="WEBHOOK", font=('Arial', 12, 'bold'))
        webhook_label.grid(row=0, column=0, padx=10, pady=5, sticky='w')

        self.webhook_entry = ttk.Entry(main_frame, font=('Arial', 12), width=25)
        self.webhook_entry.insert(0, self.config['_CORE']['WEBHOOK_URL'])  # Set default value from config
        self.webhook_entry.grid(row=0, column=1, padx=10, pady=5)

        # Server URL field
        server_label = ttk.Label(main_frame, text="PRIVATE SERVER", font=('Arial', 12, 'bold'))
        server_label.grid(row=1, column=0, padx=10, pady=5, sticky='w')

        self.server_entry = ttk.Entry(main_frame, font=('Arial', 12), width=25)
        self.server_entry.insert(0, self.config['_CORE']['SERVER_URL'])  # Set default value from config
        self.server_entry.grid(row=1, column=1, padx=10, pady=5)

        # Add Start and Stop Buttons side by side in a separate frame
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20, sticky="ew")
        
        # Configure columns of button_frame to expand and make buttons take up maximum space
        button_frame.grid_columnconfigure(0, weight=1)
        
        self.start_button = ttk.Button(button_frame, text="START", command=self.start, style='Start.TButton')
        self.start_button.grid(row=0, column=0, padx=5, sticky="ew")

        # Add some styling
        style = ttk.Style()
        style.configure('Start.TButton', font=('Arial', 14), padding=10, background="#4CAF50", foreground="black")

        # Configure the grid to expand properly
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        # Flag to control when the monitoring is running
        self.app_running = False

    def __getLogger(self, method_name):
        return logging.getLogger(f'abyssal.{method_name}')

    async def handle_biome_change(self, old_biome, new_biome):
        l = self.__getLogger('handle_biome_change')
        
        if self.qty_biome_changes == 0: l.info("ATTENTION: I WILL NOT COUNT CHANGES TO NORMAL AS A BIOME CHANGE, THE COUNTER ONLY INCREMENTS IF IT GOES TO AN USEFUL BIOME, NORMAL IS JUST BASE BIOME SO IT SHOULD NOT COUNT AS BIOME CHANGE. THANKYOU")
        
        self.qty_biome_changes += 1
        l.info(f'[#{self.qty_biome_changes}] BIOME CHANGE! From "{old_biome}" to "{new_biome}"')
        
        if new_biome == "NORMAL": return  # We don't care about the "NORMAL" biome
        
        if new_biome in ['GRAVEYARD', 'PUMPKIN MOON', 'SAND STORM', 'STARFALL']:
            l.info('INTERESTING BIOME DETECTED! Waiting until next non-normal change...')
        elif new_biome not in ['GLITCHED']:
            l.info(f'{new_biome}, Ew! Rejoining.')
            await self.roblox_app.rejoin(url=self.config['_CORE']['SERVER_URL'], join_delay_seconds=15)

    def start(self):
        # Update the config with values from the form entries
        self.config['_CORE']['WEBHOOK_URL'] = self.webhook_entry.get()
        self.config['_CORE']['SERVER_URL'] = self.server_entry.get()

        # Save the updated configuration
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)

        # destroy tkinter window
        self.window.destroy()

        # Start monitoring in a separate thread
        if not self.app_running:
            self.app_running = True
            
            if not self.roblox_app.is_running():
                asyncio.run(self.roblox_app.join(url=self.config['_CORE']['SERVER_URL']))
                
            asyncio.run(self.roblox_app.biome_monitor_start(rejoin_url=self.config['_CORE']['SERVER_URL']))
            
    def stop(self):
        self.roblox_app.biome_monitor_stop()
        self.app_running = False

    def run(self):
        # Run the Tkinter window
        self.window.mainloop()
        while self.app_running:
            time.sleep(1)

# Start the application
app = Application()
app.run()
