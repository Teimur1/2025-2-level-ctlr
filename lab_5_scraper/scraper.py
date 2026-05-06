"""
Crawler implementation.
"""

# pylint: disable=too-many-arguments, too-many-instance-attributes, unused-import, undefined-variable, unused-argument
import datetime
import json
import pathlib
import re

import requests
from bs4 import BeautifulSoup, Tag

from core_utils.article.article import Article
from core_utils.config_dto import ConfigDTO

class IncorrectSeedURLError(Exception): pass
class NumberOfArticlesOutOfRangeError(Exception): pass
class IncorrectNumberOfArticlesError(Exception): pass
class IncorrectHeadersError(Exception): pass
class IncorrectEncodingError(Exception): pass
class IncorrectTimeoutError(Exception): pass
class IncorrectVerifyError(Exception): pass


class Config:
    """
    Class for unpacking and validating configurations.
    """

    def __init__(self, path_to_config: pathlib.Path) -> None:
        """
        Initialize an instance of the Config class.

        Args:
            path_to_config (pathlib.Path): Path to configuration.
        """
        self.path_to_config = path_to_config
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            self.config_params = json.load(f)

        self._validate_config_content()
        
        self._seed_urls = self.config_params['seed_urls']
        self._num_articles = self.config_params['total_articles_to_find_and_parse']
        self._headers = self.config_params['headers']
        self._encoding = self.config_params['encoding']
        self._timeout = self.config_params['timeout']
        self._should_verify_certificate = self.config_params['should_verify_certificate']
        self._headless_mode = self.config_params['headless_mode']
        
        self.config_dto = self._extract_config_content()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Get config values.

        Returns:
            ConfigDTO: Config values
        """
        return ConfigDTO(
            seed_urls=self._seed_urls,
            total_articles_to_find_and_parse=self._num_articles, 
            headers=self._headers,
            encoding=self._encoding,
            timeout=self._timeout,
            should_verify_certificate=self._should_verify_certificate,
            headless_mode=self._headless_mode
        )

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters are not corrupt.
        """
        params = self.config_params

        seed_urls = params.get('seed_urls')
        if not isinstance(seed_urls, list) or not seed_urls:
            raise IncorrectSeedURLError
        
        for url in seed_urls:
            if not isinstance(url, str) or not re.match(r'https?://(www.)?', url):
                raise IncorrectSeedURLError

        num_articles = params.get('total_articles_to_find_and_parse')
        if not isinstance(num_articles, int) or isinstance(num_articles, bool) or num_articles <= 0:
            raise IncorrectNumberOfArticlesError
        
        if num_articles > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(params.get('headers'), dict):
            raise IncorrectHeadersError

        timeout = params.get('timeout')
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 0 < timeout <= 60:
            raise IncorrectTimeoutError

        if not isinstance(params.get('encoding'), str):
            raise IncorrectEncodingError

        if not isinstance(params.get('should_verify_certificate'), bool) or \
           not isinstance(params.get('headless_mode'), bool):
            raise IncorrectVerifyError
        
    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls.

        Returns:
            list[str]: Seed urls
        """
        return self.config_dto.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape.

        Returns:
            int: Total number of articles to scrape
        """
        return self.config_dto.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting.

        Returns:
            dict[str, str]: Headers
        """
        return self.config_dto.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing.

        Returns:
            str: Encoding
        """
        return self.config_dto.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response.

        Returns:
            int: Number of seconds to wait for response
        """
        return self.config_dto.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate.

        Returns:
            bool: Whether to verify certificate or not
        """
        return self.config_dto.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode.

        Returns:
            bool: Whether to use headless mode or not
        """
        return self.config_dto.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Deliver a response from a request with given configuration.

    Args:
        url (str): Site url
        config (Config): Configuration

    Returns:
        requests.models.Response: A response from a request
    """
    response = requests.get(
        url,
        headers=config.get_headers(),
        timeout=config.get_timeout(),
        verify=config.get_verify_certificate()
    )
    response.encoding = config.get_encoding()
    return response


class Crawler:
    """
    Crawler implementation.
    """

    #: Url pattern
    url_pattern: re.Pattern | str

    def __init__(self, config: Config) -> None:
        """
        Initialize an instance of the Crawler class.

        Args:
            config (Config): Configuration
        """
        self.config = config
        self.urls = []

        

    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.Tag): Tag instance

        Returns:
            str: Url from HTML
        """
        href = article_bs.get('href') 
        if not href or not isinstance(href, str):
            return ""
        
        if href.startswith('/'):
            return f"https://ru.wikisource.org{href}"
            
        return href
    
    def find_articles(self) -> None:
        """
        Find articles.
        """
        for seed_url in self.get_search_urls():
            response = make_request(seed_url, self.config)
            if not response.ok:
                continue
            soup = BeautifulSoup(response.text, 'lxml')
            for link in soup.find_all('a'):
                url = self._extract_url(link)
                if url and url not in self.urls:
                    self.urls.append(url)
                if len(self.urls) >= self.config.get_num_articles():
                    return

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self.config.get_seed_urls()


# 10
# 4, 6, 8, 10


class HTMLParser:
    """
    HTMLParser implementation.
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initialize an instance of the HTMLParser class.

        Args:
            full_url (str): Site url
            article_id (int): Article id
            config (Config): Configuration
        """
        self.full_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(url=full_url, article_id=article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        main_content = article_soup.find('div', {'class': 'mw-parser-output'})
        if main_content:
            self.article.text = main_content.get_text(separator=' ', strip=True)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        pass

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        return datetime.datetime.now()

    def parse(self) -> Article | bool:
        """
        Parse each article.

        Returns:
            Article | bool: Article instance, False in case of request error
        """
        response = make_request(self.full_url, self.config)
        response.encoding = self.config.get_encoding()
        
        soup = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(soup)
        self._fill_article_with_meta_information(soup)
        
        return self.article


def prepare_environment(base_path: pathlib.Path | str) -> None:
    """
    Create ASSETS_PATH folder if no created and remove existing folder.

    Args:
        base_path (pathlib.Path | str): Path where articles stores
    """
    if isinstance(base_path, str):
        base_path = pathlib.Path(base_path)
        
    if base_path.exists():
        import shutil
        shutil.rmtree(base_path)

    base_path.mkdir(parents=True, exist_ok=True)

def main() -> None:
    """
    Entrypoint for scraper module.
    """
    from core_utils.constants import CRAWLER_CONFIG_PATH, ASSETS_PATH

    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    
    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=i, config=configuration)
        article = parser.parse()
        if article:
            article.save_raw()

if __name__ == "__main__":
    main()
