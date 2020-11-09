import argparse
import os
import re
import sys

import language_tool_python
import requests
from bs4 import BeautifulSoup
from scraper_api import ScraperAPIClient


def print_error_and_exit(error):
    print(error)
    sys.exit(1)


def extract_text(page_soup):
    if page_soup:
        # TODO for elem_loc in elem_locs - try except
        elem_locs = [
            "div#cs-content",
            "div.x-main",
        ]

        for elem_loc in elem_locs:
            # try:
            # print(elem_loc)
            elem = page_soup.select_one(elem_loc) or ""

            # except:
            #     continue
            if elem:
                # print("IN ELEM")
                all_white_space_pattern = re.compile(r"\s+")
                text_without_extra_whitespace = re.sub(
                    all_white_space_pattern, " ", elem.get_text()
                )

                return text_without_extra_whitespace


def is_bad_match(match):
    if "Possible spelling mistake found." in match.message:
        excluded_text = [
            # Persons
            "Pardeep",
            "Boparai",
            "Renaldi",
            "Sibarani",
            "Maciek",
            "Dworaczyk",
            "Kuan",
            # Other
            "Pte",
            "DTAs",
            "Singlish",
            "EngLISH",
            "SINGapore",
            "laksa",
            "prata",
            "roti",
            "Merlion",
            "ArtScience",
            "Skytrax",
            "Changi",
        ]

        if any(match.matchedText.lower() in text.lower() for text in excluded_text):
            print("Excluding word:", match.matchedText)

            return match


def check_text(extracted_text, CHECK_TOOL):
    if extracted_text and CHECK_TOOL:
        matches = CHECK_TOOL.check(extracted_text)

        relevant_matches = []

        for match in matches:
            if not is_bad_match(match):
                relevant_matches.append(match)

        # print(relevant_matches)

        corrections = []

        for relevant_match in relevant_matches:
            correction_info = []

            correction_info.append(relevant_match.category)
            correction_info.append(relevant_match.message)
            correction_info.append(relevant_match.matchedText)
            correction_info.append(relevant_match.context)

            corrections.append(correction_info)
            # print(correction_info)

        # print(checked_text)
        # print(corrections)

        return corrections


def get_page_soup(client, url):
    try:
        url_page = client.get(url)

    except requests.exceptions.ConnectionError:
        print_error_and_exit("Page connection error")

    if url_page.status_code != 200:
        print(url_page.status_code)
        print_error_and_exit("Page not found or access error")

    # if "Enter characters you see below" in product_page.text:
    #     print("CAPTCHA page is displayed")
    #     return None

    page_soup = BeautifulSoup(url_page.text, "lxml")

    return page_soup


def create_dir():
    ABS_PATH = os.path.abspath(__file__)
    BASE_DIR = os.path.join(os.path.dirname(ABS_PATH), "guides-corrections")

    if not os.path.exists(BASE_DIR):
        os.mkdir(BASE_DIR)

    return BASE_DIR


def write_result_to_file(check_results, idx):
    if None not in check_results.items():
        BASE_DIR = create_dir()

        # print(check_results)
        for url, corrections in check_results.items():
            if url and corrections:
                if url.endswith("/"):
                    url_file_name = url.split("/")[:-1][-1]

                else:
                    url_file_name = url.split("/")[-1]

                file_name = str(idx) + "-" + url_file_name + ".txt"

                with open(
                    os.path.join(BASE_DIR, file_name), "w", encoding="utf-8"
                ) as check_results_file:

                    check_results_file.write(url + "\n")

                    for relevant_match in corrections:
                        for correction_info in relevant_match:
                            check_results_file.write("\n" + str(correction_info))
                        check_results_file.write("\n")


def check_urls(client):
    if client:
        CHECK_TOOL = language_tool_python.LanguageTool("en-US")

        BASE_URL = "https://www.corporateservices.com"
        base_page_soup = get_page_soup(client, BASE_URL + "/singapore/")

        # print(base_page_soup)
        links_soup = base_page_soup.select("#toc a")

        idx = 1

        for link_soup in links_soup[:5]:
            if link_soup:
                check_results = {}
                url = link_soup["href"]

                if not url.startswith(BASE_URL):
                    if url.startswith(".."):
                        url = url[2:]

                    url = BASE_URL + url

                if not url.endswith("/"):
                    url += "/"

                print(url)
                page_soup = get_page_soup(client, url)
                extracted_text = extract_text(page_soup)
                # print(extracted_text)
                check_results[url] = check_text(extracted_text, CHECK_TOOL)
                # print(check_results)

                write_result_to_file(check_results, idx)

                idx += 1


def parse_args():
    arg_parser = argparse.ArgumentParser(
        description="Scrap information from pages and lang process it"
    )

    arg_parser.add_argument(
        "-k",
        action="store",
        dest="api_key",
        required=True,
        type=str,
        help="Scraper API key",
    )

    return arg_parser.parse_args()


def connect_to_api(api_key):
    try:
        client = ScraperAPIClient(api_key)
        status = client.account()

    except requests.exceptions.ConnectionError:
        print_error_and_exit("Connection error")

    if "error" in status:
        print_error_and_exit("Scraper API key error")

    return client


def main():
    parsed_args = parse_args()
    api_key = parsed_args.api_key

    client = connect_to_api(api_key)
    check_urls(client)


if __name__ == "__main__":
    main()
