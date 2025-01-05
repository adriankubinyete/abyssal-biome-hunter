import os
import json
import time
import psutil
import asyncio
import logging
from urllib.parse import urlparse, parse_qs # for private server links
from datetime import datetime
from pathlib import Path
from .system import System

class RobloxApplication:
    def __init__(self):
        self.processes = []
        self.log_name = 'abyssal.Roblox.'
        self.LOGFILE_DETECTION_METHOD = 'accesstime' # accesstime | filename
        self.ALWAYS_SEND_LATEST_BIOME = False
        
        # --- SOLS STUFF ---
        self.ready_to_notify = None
        self.last_biome = None
        self.on_biome_change_callback = None
        self.is_running_biome_monitor = False
        # --- END SOLS STUFF ---
        
    def __getLogger(self, name):
        return logging.getLogger(self.log_name + name)

    def update_processes(self, min_runtime_seconds=10):
        """
        Updates Roblox's process list with detailed info.
        """
        l = self.__getLogger('update_processes')
        self.processes = []
        current_time = time.time()  # Tempo atual em segundos desde a época (Unix)
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
            if 'RobloxPlayerBeta.exe' in proc.info['name']:
                # Verifica se o processo está rodando há mais de 'min_runtime_seconds' segundos
                runtime = current_time - proc.info['create_time']
                if runtime > min_runtime_seconds:
                    self.processes.append(proc.info)
                else:
                    l.trace(f"Process {proc.info['name']} (PID: {proc.info['pid']}) is running for less than {min_runtime_seconds} seconds. Waiting until ready.")
                    time.sleep(min_runtime_seconds - runtime + 1)  # awaits remaining time, and/or at least 1 second

    def is_running(self, *args, **kwargs):
        """Verifica se o Roblox está em execução."""
        l = self.__getLogger('is_running')
        self.update_processes(*args, **kwargs)
        return len(self.processes) > 0

    def get_latest_log(self):
        """Encontra o log mais recente que contém 'Player' e termina com '_last.log'."""
        l = self.__getLogger('get_latest_log')  # Obtém o logger para a função
        
        # Only try to get the latest log if the Roblox is running
        # Process has to be running for at least 10 seconds to be considered active
        if not self.is_running(min_runtime_seconds=15):
            l.debug('Roblox is not running.')
            return None

        # @FIXME: MAKE SURE THIS IS COMPATIBLE WITH WINDOWS AND LINUX?
        # GET THIS FROM CURRENT APP ID EXECUTABLE PATH INSTEAD OF "HARDCODING" IT
        # Directory until the Roblox logs directory
        logs_dir = Path.home() / "AppData" / "Local" / "Roblox" / "logs"

        if not logs_dir.exists():
            l.error(f"Log directory not found: {logs_dir}")
            return None

        # Filter files with "Player" and ending with '_last.log'
        log_files = [
            log_file for log_file in logs_dir.glob("*.log")
            if "Player" in log_file.name and log_file.name.endswith("_last.log")
        ]

        if not log_files:
            l.error("No log file found.")
            return None

        # # DEBUG: Uncommenting this will print every log file and its last access time
        # for log_file in log_files:
        #     l.debug(f"LOG_FILE_NAME: {log_file.name}, FILE_TIME: {datetime.fromtimestamp(log_file.stat().st_atime)}")

        # Select the most recent log based on file modification time
        
        
        # @TODO: try filename method, if fails for RPC, try accesstime method
        if self.LOGFILE_DETECTION_METHOD == "filename":
            # break log names by underscores and take the second part (a timestamp formatted as 20250104T012925Z)
            latest_log = max(log_files, key=lambda f: datetime.strptime(f.name.split('_')[1], "%Y%m%dT%H%M%SZ"))
            # l.debug(f"Latest log via filename is {latest_log}")
        elif self.LOGFILE_DETECTION_METHOD == "accesstime":
            latest_log = max(log_files, key=lambda f: f.stat().st_atime)
            # l.debug(f"Latest log via last access time is {latest_log}")
        else:
            l.error("Invalid method. Use 'filename' or 'accesstime'.")
            return None
        
        return {
        "path": latest_log, # full path including log file
        "filename": latest_log.name, # 0.654.1.6540477_20250105T013421Z_Player_E45D9_last
        "short_identifier": latest_log.name.split('_')[3], # E45D9
        "timestamp_filename": latest_log.name.split('_')[1], # 20250105T013421Z
        "last_modified": latest_log.stat().st_atime,
        }


    def display_latest_log(self):
        """
        Shows the content of the latest log file in the terminal.
        """
        l = self.__getLogger('display_latest_log')
        log = self.get_latest_log()
        if log:
            with open(log['path'], "r", encoding="utf-8") as log_file:
                l.debug(log_file.read())
                
    # --------- SOLS RNG SPECIFIC STUFF ---------
    
    def print_bloxstrap_rpc_entries(self):
        """
        DEBUG ONLY. 
        This will print straight to console the entire BloxstrapRPC log for the latest log file found.
        """
        l = self.__getLogger('print_bloxstrap_rpc_entries')
        log = self.get_latest_log()
        if log:
            last_rpc_entry = None
            with open(log['path'], "r", encoding="utf-8") as log_file:
                for line in log_file:
                    if "BloxstrapRPC" in line:
                        l.info(f"{line.strip()}")
        
    def get_latest_rpc_log_entry(self):
        """
        This function is supposed to obtain the latest log entry that contains the text 'BloxstrapRPC'.
        It returns the entire line, or None if no entries is found.
        """
        l = self.__getLogger('get_latest_rpc_log_entry')
        
        log = self.get_latest_log()
        if log:
            last_rpc_entry = None
            with open(log['path'], "r", encoding="utf-8") as log_file:
                for line in log_file:
                    if "BloxstrapRPC" in line:
                        last_rpc_entry = line.strip()
            
            if last_rpc_entry:
                # l.trace(f"{last_rpc_entry}")
                return last_rpc_entry
            else:
                l.warning(f"{log['short_identifier']} :: T-{log['timestamp_filename']}/LA-{log['last_modified']} : No BloxstrapRPC entry found in log file.")
        return None
    
    def get_latest_rpc_command(self):
        """
        This function's purpose is to extract the command from the latest RPC log entry.
        It returns the command as a dictionary, or None if no entry is found.
        """
        l = self.__getLogger('get_latest_rpc_command')
        latest_rpc_entry = self.get_latest_rpc_log_entry()
        if latest_rpc_entry:
            command = latest_rpc_entry.split("[BloxstrapRPC]")[1].strip()
            # l.trace(f"Latest RPC command: {command}")
            
            # Attempt to parse the command as JSON
            try:
                command_dict = json.loads(command)
            except json.JSONDecodeError:
                l.critical("Failed to parse latest RPC command.")
                return None
            return command_dict
        # # This else is redundant, as get_latest_rpc_log_entry() already tells you something is wrong
        # else:
        #     # theres no rpc command, but game is running
        #     if self.is_running():
        #         l.trace("No RPC command found in log file. Roblox is probably getting started, or got stuck before logging into Sol's RNG (i.e. Error screen)")
        return None
    
    def get_latest_biome(self):
        """
        This function's purpose is to extract the biome from the latest RPC command.
        It returns the biome as a string, or None if no command is found.
        """
        l = self.__getLogger('get_latest_biome')
        latest_rpc_command = self.get_latest_rpc_command()
        
        if latest_rpc_command:
            try:
                data = latest_rpc_command.get("data", {})
                largeImage = data.get("largeImage", None)
                biome = largeImage.get("hoverText", None)
                if self.ALWAYS_SEND_LATEST_BIOME: l.debug(f'{biome}')
                return biome
            except (json.JSONDecodeError, TypeError):
                l.error("Failed to parse latest RPC command.")
        
        return None
    
    def on_biome_change(self, callback):
        """
        Registers callback that will be called once biome changes.
        """
        self.on_biome_change_callback = callback
        
    async def biome_monitor_start(self, rejoin_url=None, max_fails=20):
        """
        Starts infinite loop that will read current biome.
        Should be called asynchronously.
        """
        l = self.__getLogger('biome_monitor_start')
        
        self.is_running_biome_monitor = True
        
        fail_counter = 0
        max_fail_counter = max_fails
        while self.is_running_biome_monitor:
            biome = self.get_latest_biome()

            if biome:
                fail_counter = 0
                if self.last_biome != biome: # biome changed
                    await self.on_biome_change_callback(old_biome=self.last_biome, new_biome=biome) # fires callback
                    self.last_biome = biome # updates current
            else:
                if self.last_biome: 
                    l.info(f"Roblox closed/crashed.")
                else:
                    fail_counter += 1
                    if fail_counter % 5 == 0:
                        l.debug(f"[#{fail_counter}] Failed to get latest biome. Roblox is either: 1. not open, 2. stuck at an errorcode screen or 3. stuck at loading data.")
                self.last_biome = None
                
                if fail_counter >= max_fail_counter:
                    
                    if rejoin_url:
                        l.warning("Too many failed attempts to get biome. Rejoining...")
                        fail_counter = 0
                        await self.rejoin(url=rejoin_url)
                    else:
                        self.is_running_biome_monitor = False
                        l.critical("Too many failed attempts to get biome. Exiting...")
                        raise  Exception("Too many failed attempts to get biome.")
            
            time.sleep(1)
            
    def biome_monitor_stop(self):
        """
        Stops infinite loop that will read current biome.
        """
        l =  self.__getLogger('biome_monitor_stop')
        self.is_running_biome_monitor = False
        
    async def close(self):
        """
        Closes Roblox application.
        """
        l = self.__getLogger('close')

        l.test(f'Registered processes: {self.processes}')
        # go over every open process and kill it with system._taskkill
        
        if self.processes:
            for process in self.processes:
                l.trace(f"Killing process {process['name']} with PID {process['pid']}")
                await System._taskkill(process['pid'])
            self.processes = []
            l.info("Roblox closed.")
            
    async def join(self, url, force_join=False):
        """
        Joins Roblox game with given URL.
        """
        l = self.__getLogger('join')

        if not force_join:
            if self.is_running():
                l.trace("Roblox is already running.")
                return

        FINAL_URL = f"roblox://placeID=15532962292&linkCode={parse_qs(urlparse(url).query).get("privateServerLinkCode", [None])[0]}"
        
        l.info(f'Joining: {FINAL_URL}')
        await System._start(url=FINAL_URL)
        
    async def rejoin(self, url, join_delay_seconds=15):
        """
        Rejoins Roblox game with given URL.
        """
        l = self.__getLogger('rejoin')
        
        # await self.close()
        # l.info(f"Waiting {join_delay_seconds} seconds before rejoining...")
        # await asyncio.sleep(join_delay_seconds)
        l.test("Join game directly without quitting previously")
        await self.join(url, force_join=True) 