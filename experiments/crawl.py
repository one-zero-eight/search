from html_to_markdown.exceptions import ConversionError
import json
import os
from http.cookiejar import CookieJar, DefaultCookiePolicy
from pathlib import Path
from catix.wiki.sources.sites import _Markdown
import tempfile
import httpx
from html_to_markdown import convert, ConversionOptions, VisitorHandle, VisitResult, NodeContent, NodeContext
from catix.wiki.sources import regulations, sites
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

class VisitorPage:
    def __init__(self, url: str):
        self.url=url
    def visit_image(self, ctx, src, alt, title=None):
        absolute_url= urljoin(self.url, src)
        return {"type": "custom", "output": f"![{alt}]({absolute_url})"}

    @classmethod
    def builder(cls, url: str):
        return VisitorPage(url=url)



class VisitorJSGuard:
    def visit_element_end(self, ctx: NodeContext, output: str):
        # Raise error when this page need a javascript
        if ctx.tag_name == "noscript" and "javascript" in output.lower():
            return {"type": "error", "output": "javascript"}
        return {"type": "continue"}


def parse_with_broswer(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=False,
                                    args=['--no-sandbox'])
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("body")
        return page.content()
def main():
    # tempdir = tempfile.mkdtemp()
    # tempdir = Path(tempdir)
    # print(tempdir)
    with httpx.Client(
        headers=regulations.HEADERS,
        follow_redirects=True,
        timeout=30,
        cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])),
    ) as client:
        for name, url in [
            # ("fmp", "https://fmp.innopolis.university/"),
            # ("fizmat", "https://fizmat.innopolis.university/"),
            ("lyceuminnopolis-ru", "https://lyceuminnopolis.ru"),
            # ("my", "https://my.innopolis.university/store"),
        ]:

            response = client.get(url)

            print(
                name,
                response.status_code,
                str(response.url),
                response.headers.get("content-type"),
                flush=True,
            )
        #     if name == "my":
        #         print(
        #             "login form",
        #             bool(sites.LOGIN_FORM.search(response.text)),
        #             flush=True,
        #         )
        #         continue
            #         o
            try:
                comperor = convert(response.text, ConversionOptions(extract_images=False, inline_data_media="alt_text_only", hidden_content="all" ), visitor=VisitorJSGuard())
            except ConversionError as e:
                if not str(e).endswith("javascript"):
                    raise 
                content = parse_with_broswer(url)
                comperor = convert(content, ConversionOptions(extract_images=False, inline_data_media="alt_text_only"), visitor=VisitorPage.builder(url))
            

            # (tempdir / (name + ".md")).write_text(comperor.content)
            print(list(map(lambda x: x.href, comperor.metadata.links)))
            print(comperor.content)
            

            
            # print(
            #     title,
            #     "links",
            #     len(links),
            #     "images",
            #     text.count("!["),
            #     flush=True,
            # )
            # print(
            #     [
            #         link
            #         for link in links
            #         if "fizmat" in link[0] or name == "lyceuminnopolis-ru"
            #     ],
            #     flush=True,
            # )


if __name__ == "__main__":
    main()
