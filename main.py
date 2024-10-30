import argparse
import html
import os
import re
from hashlib import md5
from pathlib import Path
from urllib.parse import urlparse

import requests
from readability import Document
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CLEAN = re.compile("<.*?>")
DEFAULT_OUTPUT_PATH = Path("~/Documents/URL Text/").expanduser()
FILETYPE = ".txt"
CONFIRM_STRINGS = ["y", "yes"]


def mkdirs(dir_path: Path) -> None:
    os.makedirs(dir_path, exist_ok=True)


def is_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def generate_output_name(index: int, url: str) -> str:
    parsed_url = urlparse(url)
    md5_hash = md5(url.encode()).hexdigest()[:8]
    base_name = f"{index}-{parsed_url.netloc}-{md5_hash}"
    return f"{base_name}.txt"


def get_session() -> requests.Session:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0.1 Safari/605.1.15"
    }
    session = requests.Session()
    session.headers.update(headers)
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def extract_text(session: requests.Session, url: str) -> str:
    if not is_url(url):
        raise ValueError(f"{url} is not a url.")
    try:
        response = session.get(url, allow_redirects=False)
        response.raise_for_status()
        doc = Document(response.content)
        text = f"{doc.title()}\n{doc.summary()}"
        text = re.sub(CLEAN, "", text)
        return html.unescape(text)
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
    except Exception as e:
        print(f"Failed to extract text for {url}: {e}")
    return ""


def init_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="""
        This script reads URLs from a specified text file, retrieves the main content 
        from each URL, cleans the extracted text by removing HTML tags, and saves the 
        output to a designated directory. Users can specify a custom output directory 
        or use the default location. Each URL's content is saved as a separate .txt file.
        """
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Path to the text file containing URLs, with one URL per line.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Directory where extracted text files will be saved. Defaults to {DEFAULT_OUTPUT_PATH}.",
        required=False,
        type=str,
    )
    return parser


class WebTextExtractor:
    def __init__(self, file: Path, output_path: Path) -> None:
        self.file = file
        self.output_path = output_path
        if not self.file.exists():
            raise ValueError(f"File {self.file} does not exist.")
        if self.file.suffix != FILETYPE:
            raise ValueError(f"File {self.file} is not a text file.")
        if self.output_path.is_file():
            raise ValueError(f"Output path {self.output_path} is not a directory.")
        if not self.output_path.exists():
            if self.output_path != DEFAULT_OUTPUT_PATH:
                print(f"Output path {self.output_path} does not exist.")
                confirm_mkdir = (
                    input("Would you like to make this directory? ").lower()
                    in CONFIRM_STRINGS
                )
                if confirm_mkdir:
                    self.output_path = self.output_path
                else:
                    self.output_path = DEFAULT_OUTPUT_PATH
                    print(f"Output path set to {self.output_path}")
            mkdirs(self.output_path)

        self.session = get_session()

    def read(self) -> None:
        with open(self.file, "r") as f:
            urls = f.readlines()
            for index, url in enumerate(urls):
                url = url.strip()
                if not is_url(url):
                    continue
                print(url)
                text = extract_text(self.session, url)
                name = generate_output_name(index, url)
                with open(self.output_path / name, "w") as output:
                    output.write(text)


def main() -> None:
    parser = init_parser()
    args = parser.parse_args()
    reader = WebTextExtractor(file=Path(args.file), output_path=Path(args.output))
    reader.read()


if __name__ == "__main__":
    main()
