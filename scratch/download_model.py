import os
import requests
import sys

def download():
    url = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    target_path = os.path.join(model_dir, "llama-3.2-3b.Q4_K_M.gguf")
    
    if os.path.exists(target_path):
        print(f"Model already exists at {target_path}")
        return

    print(f"Downloading from {url}...")
    headers = {"User-Agent": "HF-Hub/1.0"}
    response = requests.get(url, headers=headers, stream=True)
    if response.status_code != 200:
        print(f"Error: Server returned status code {response.status_code}")
        return

    total_size = int(response.headers.get('content-length', 0))
    print(f"Total size: {total_size / (1024*1024):.2f} MB")
    sys.stdout.flush()
    
    downloaded = 0
    last_printed = 0
    chunk_size = 1024 * 1024  # 1MB
    
    with open(target_path + ".tmp", "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded - last_printed >= 10 * 1024 * 1024:  # Print every 10MB
                    print(f"Progress: {downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB ({downloaded/total_size*100:.1f}%)")
                    sys.stdout.flush()
                    last_printed = downloaded
                    
    if os.path.exists(target_path):
        os.remove(target_path)
    os.rename(target_path + ".tmp", target_path)
    print(f"Model successfully saved to {target_path}")
    sys.stdout.flush()

if __name__ == "__main__":
    download()
