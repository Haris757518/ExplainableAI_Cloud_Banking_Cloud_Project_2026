from dataset.generator import read_jsonl

def load_dataset(path: str):
    return read_jsonl(path)
