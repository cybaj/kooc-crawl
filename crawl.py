from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
import m3u8
import os
import subprocess
import time
import sys
from .targets import default_targets as targets

LOGIN_URL = 'https://kaist.edwith.org/neoid/emailLogin'
BASE_URL = 'https://kooc.kaist.ac.kr/physics-gap-1'
HLS_BASE_URL = 'https://b01-kr-naver-vod.pstatic.net'

username = sys.argv[1]
password = sys.argv[2]
if not username or not password:
    print("Please provide username and password")
    sys.exit(1)
USERNAME = username
PASSWORD = password

def login(driver):
    driver.get(LOGIN_URL)
    # Wait for the login form to be present
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'email'))
    )
    # Enter username
    username_field = driver.find_element(By.NAME, 'email')
    username_field.send_keys(USERNAME)
    # Enter password
    password_field = driver.find_element(By.NAME, 'password')  # Replace with the actual name attribute of the password field
    password_field.send_keys(PASSWORD)
    # Submit the login form
    login_button = driver.find_element(By.ID, 'submit')  # Replace with the actual name attribute of the login button
    login_button.click()

    # Wait for the login to complete, e.g., by waiting for a specific element on the post-login page
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'modal_wrap'))  # Replace with an actual element present after login
    )

def get_page_urls(driver, main_url):
    driver.get(main_url)
    page_urls = []

    # Wait for the main page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'ol.lect_2dep'))
    )

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'li.active'))
    )

    # Locate the hierarchy and extract URLs
    active_elements = driver.find_elements(By.CSS_SELECTOR, 'li.active')
    for active_element in active_elements:
        div_elements = active_element.find_elements(By.TAG_NAME, 'div')
        if len(div_elements) == 0:
            continue
        for a_element in active_element.find_elements(By.CSS_SELECTOR, 'ol.lect_2dep a'):
            page_url = a_element.get_attribute('href')
            if page_url and "lecture" in page_url:
                page_urls.append(page_url)

    return page_urls

def get_streaming_url(page_url, driver):
    driver.get(page_url)

    WebDriverWait(driver, 10).until(
        EC.all_of(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'section.page')),
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'div.user_info_view')),
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'div.group_lr'))
        )
    )

    content_div = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'content'))  # Replace with the actual selector
    )

    movie_divs = driver.find_elements(By.ID, 'movie')
    if len(movie_divs) == 0:
        return False

    streaming_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.play'))  # Replace with the actual selector
    )
    # streaming_button.click()
    driver.execute_script("arguments[0].click();", streaming_button)

    # Wait for the network request containing the m3u8 URL
    WebDriverWait(driver, 10).until(lambda d: any('m3u8' in request.path for request in d.requests))
    m3u8_url = None
    for request in reversed(driver.requests):
        if request.response and 'm3u8' in request.path:
            m3u8_url = request.url
            response = requests.get(m3u8_url)
            m3u8_master = m3u8.loads(response.text)
            if len(m3u8_master.segments) == 0:
                continue
            break

    title_h = driver.find_element(By.CSS_SELECTOR, 'h1.page_title')

    if m3u8_url:
        return m3u8_url, title_h.text
    else:
        raise Exception("m3u8 URL not found")

def download_m3u8(m3u8_url):
    response = requests.get(m3u8_url)
    m3u8_master = m3u8.loads(response.text)
    tss = [segment.uri for segment in m3u8_master.segments]

    base_url = m3u8_url[:m3u8_url.rfind('/')]
    params = m3u8_url[m3u8_url.rfind('?'):]
    return [base_url + '/' + ts + params for ts in tss]

def download_segments(ts_urls, video_name):
    os.makedirs('videos/tmp', exist_ok=True)
    ts_files = []
    for idx, url in enumerate(ts_urls):
        ts_file = f'videos/tmp/{video_name}_{idx}.ts'
        ts_files.append(ts_file)
        with open(ts_file, 'wb') as f:
            response = requests.get(url, stream=True)
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
    return ts_files

def merge_segments(ts_files, output_file):
    temp_name = output_file.split('/')[-1].split('.')[0]
    ts_list_path = f'videos/tmp/ts_files_{temp_name}.txt'
    if os.path.exists(ts_list_path):
        os.remove(ts_list_path)

    with open(ts_list_path, 'w') as f:
        for ts_file in ts_files:
            f.write(f"file '{os.path.abspath(ts_file)}'\n")

    # Use ffmpeg to merge ts files into a single mp4 file
    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', ts_list_path, '-c', 'copy', output_file])


def download_lecture(driver, main_url, lecture_name):
    page_urls = get_page_urls(driver, main_url)

    os.makedirs(f'outputs/{lecture_name}', exist_ok=True)

    for i, page_url in enumerate(page_urls):
        print(f'Downloading video from {page_url}')
        try:
            streaming_url_and_video_title = get_streaming_url(page_url, driver)
            if streaming_url_and_video_title:
                streaming_url, video_title = streaming_url_and_video_title

                if os.path.exists(f'outputs/{lecture_name}/video_{i+1}_{video_title}.mp4'):
                    continue

                ts_urls = download_m3u8(streaming_url)

                ts_files = download_segments(ts_urls, f'video_{i+1}')
                merge_segments(ts_files, f'outputs/{lecture_name}/video_{i+1}_{video_title}.mp4')
                print(f'Video {i+1} downloaded.')
        except Exception as e:
            print(f'Failed to download video from {page_url}: {e}')
            with open("failed.txt", 'a') as f:
                f.writelines(lecture_name + " " + page_url)
def main():
    driver = webdriver.Chrome()

    login(driver)

    for main_url, lecture_name in targets:
        download_lecture(driver, main_url, lecture_name)
