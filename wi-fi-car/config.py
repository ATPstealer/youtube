"""Loads config.ini - the hand-edited settings. The UI-tuned trim lives in settings.json."""
import configparser
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(BASE_DIR, 'config.ini')


def load(path=DEFAULT_PATH):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path} (config.ini must be next to app.py)")
    cfg = configparser.ConfigParser(inline_comment_prefixes=('#',))
    cfg.read(path, encoding='utf-8')
    return cfg
