import logging
import subprocess

class System():
    def __init__(self):
        self.log_name = 'abyssal.System.'

    def __getLogger(self, name):
        return logging.getLogger(self.log_name + name)
    
    # --- PROCCESS RELATED ---
    
    async def __execute_command(self, command):
        '''
        command : string with command to be executed
        example: self._execute_command("taskkill /im python.exe /f")
        '''
        l = self.__getLogger('execute_command')
        
        try:
            l.trace(f"Executing command: {command}")
            subprocess.run(command, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed: {e}")
        
    async def _taskkill(self, process_id):
        '''
        process_id : int with process id
        example: self.taskkill(12345)
        '''
        l = self.__getLogger('kill')
        
        try:
            # mute the output of this command
            
            await self.__execute_command(f"taskkill /F /PID {process_id}")
        except Exception as e:
            l.exception(f"Failed to kill process: {e}")
            raise RuntimeError(f"Failed to kill process: {e}")
        
    async def _start(self, url):
        '''
        url : string with url to be opened
        example: self.start("https://www.google.com")
        '''
        l = self.__getLogger('start')

        try:
            # l.trace(f'Starting URL: {url}')
            await self.__execute_command(f'start "" "{url}"')
        except Exception as e:
            l.exception(f"Failed to start URL: {e}")
            raise RuntimeError(f"Failed to start URL {url}: {e}")
        
System = System()