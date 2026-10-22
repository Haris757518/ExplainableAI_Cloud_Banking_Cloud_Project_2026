from .parser import parse

def extract(html, retrieved_at, checksum):
    return parse(html, 'monzo', retrieved_at, checksum)
