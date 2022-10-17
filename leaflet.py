import requests
from utils import run
from time import sleep


def get_urls():
    host = "https://www.bbcgoodfood.com"
    next_url = f"{host}/api/lists/posts/list/healthy-vegetarian-recipes/items?page=1"
    while True:
        res = requests.get(next_url)
        res.raise_for_status()
        data = res.json()
        next_url = data["nextUrl"]

        for item in data["items"]:
            run(host + item["url"], True)

        sleep(5)


if __name__ == "__main__":
    get_urls()
