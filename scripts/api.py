import os

from bella.config import CONFIG


config = CONFIG['api']

os.chdir("bella_rest")
os.system(f"gunicorn bella_rest.wsgi:application -b 0.0.0.0:{config['port']}")
