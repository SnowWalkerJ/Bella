import os

from bella.config import CONFIG


config = CONFIG['api']

os.system(f"gunicorn -b 0.0.0.0:{config['port']} --pythonpath bella_rest bella_rest.wsgi:application")
