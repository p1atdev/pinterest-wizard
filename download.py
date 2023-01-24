import argparse
import requests
import json
from concurrent.futures import ThreadPoolExecutor


def download(image, output, caption_ext):
    url = image["src"]
    tags = image["tags"]
    filename = url.split("/")[-1]
    [filename, img_ext] = filename.split(".")

    img = requests.get(url, stream=True)
    if img.status_code == 200:
        with open(output + "/" + filename + "." + img_ext, "wb") as f:
            for chunk in img:
                f.write(chunk)

    with open(output + "/" + filename + "." + caption_ext, "w", encoding="utf-8") as f:
        f.write(", ".join(tags))

    print(f"Downloaded: {filename}.{img_ext}")
        
def __main__(input, limit, output, batch_size, caption_ext):
    batch_size = int(batch_size)

    with open(input, "r", encoding="utf-8") as f:
        result = json.load(f)
    
    if limit:
        result = result[:limit]

    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        executor.map(download, result, [output] * len(result), [caption_ext] * len(result), chunksize=batch_size)
    
    print("Done! Downloaded", len(result), "images to", output, "with caption extension", f".{caption_ext}")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Pinterest")
    parser.add_argument("input", type=str, help="Input json path")
    parser.add_argument("--limit", type=int, help="Number of images to download")
    parser.add_argument("--output", type=str, help="Output JSON file")
    parser.add_argument("--batch_size", type=int, default=10, help="Number of threads to fetch detail data")
    parser.add_argument("--caption_ext", type=str, default="caption", help="Caption file extension")
    args = parser.parse_args()
    __main__(args.input, args.limit, args.output, args.batch_size, args.caption_ext)