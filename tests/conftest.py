from pathlib import Path

def get_sample(*path):
    return Path(__file__).parent /"samples"/ Path(*path)