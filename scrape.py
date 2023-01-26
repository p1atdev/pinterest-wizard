import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
import json
import requests
from concurrent.futures import ThreadPoolExecutor
import time

base = "https://www.pinterest.com"

def scrape(url: str, limit: int, trial: int):
    options = ChromeOptions()
    options.add_experimental_option('prefs', {'intl.accept_languages': 'en'})
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    wait.until(lambda x: x.find_element(By.XPATH, "//div[@role='list']"))

    image_els = {}

    failed = 0

    while (True):
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # count target
        no_more_new = True
        items = soup.find_all("div", {"role": "listitem"})
        a_els = []
        for item in items:
            a_els.append(item.find("a"))
        for a in a_els:
            if a is None:
                continue
            url = a.get("href")
            if image_els.get(url) is None:
                no_more_new = False
                img_el = a.find("img")
                image_els[url] = {
                    "url": base + url,
                    "alt": img_el.get("alt"),
                    "src": img_el.get("src").replace("236x", "736x")
                }

        print("Current:", len(image_els))

        if len(image_els) >= limit:
            break
        elif no_more_new:
            failed += 1
            if failed >= trial:
                break

        # scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(1.5)

    driver.quit()

    return list(image_els.values())[:limit]

def scrape_detail_tags(url: str):
    try:
        r = requests.get(url)

        soup = BeautifulSoup(r.text, "html.parser")

        closeup_detail = soup.find("div", {"data-test-id": "CloseupDetails"})
        if closeup_detail is not None:
            vase_tags = closeup_detail.find_all("div", {"data-test-id": "vase-tag"})
            closeup_image = soup.find("div", {"data-test-id": "pin-closeup-image"})
            
            if closeup_image is None:
                # video
                closeup_body = soup.find("div", {"data-layout-shift-boundary-id": "CloseupPageBody"})
                img_src = closeup_body.find("video")
                if img_src is not None:
                    img_src = img_src.get("poster")
                else:
                    img_src = None
                    
            else:
                img_el = closeup_image.find("img", {"elementtiming": "closeupImage"})
                img_src = img_el.get("src")
        else:
            closeup_page_container = soup.find("div", {"data-layout-shift-boundary-id": "CloseupPageContainer"})
            vase_tags = closeup_page_container.find_all("div", {"data-test-id": "vase-tag"})
            img_src = closeup_page_container.find("video")
            if img_src is not None:
                img_src = img_src.get("poster")
            else:
                img_src = None

        tags = []
        for tag in vase_tags:
            tags.append(tag.find("span").text)
        
        return {
            "tags": tags,
            "src": img_src
        }
    except Exception as e:
        # retry
        print("Error:", e, url)
        return scrape_detail_tags(url)

def scrape_detail_tags_multi_wrapper(r):
    print(f"Detail data fetched: {r['url']}")
    detail = scrape_detail_tags(r["url"])
    r["tags"] = detail["tags"]
    if detail["src"] is not None:
        r["src"] = detail["src"]
    # print(r)
    return r

def fetch_detail_data(result, batch_size):
    # do something
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        result = executor.map(scrape_detail_tags_multi_wrapper, result, chunksize=batch_size)

    return result

def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def __main__(query, limit, output, trial, batch_size):
    limit = int(limit)
    trial = int(trial)
    batch_size = int(batch_size)

    url = base + "/search/pins" + "?q=" + query

    result = scrape(url, limit, trial)

    result = fetch_detail_data(result, batch_size)

    result = [v for v in result]

    save_json(result, output)

    # fix paragraph separator
    with open(output, "r", encoding="utf-8") as f:
        text = f.read()
    with open(output, "w", encoding="utf-8") as f:
        f.write(text.replace("\\u2029", "\\n"))

    print("Done!", len(result), "images saved to", output)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Pinterest")
    parser.add_argument("query", help="Search keyword")
    parser.add_argument("--limit", help="Limit the number of images to scrape", default=30)
    parser.add_argument("--output", help="Output file name", default="output.json")
    parser.add_argument("--trial", help="Number of trials to check if there are no more new images", default=10)
    parser.add_argument("--batch_size", help="Batch size for fetching detail data", default=100)
    args = parser.parse_args()
    __main__(args.query, args.limit, args.output, args.trial, args.batch_size)