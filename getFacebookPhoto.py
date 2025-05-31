import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

def save_image(url, folder, count):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            filename = os.path.join(folder, f'{count}.jpg')
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f'Saved {filename}')
        else:
            print(f'Failed to download {url}, status code: {response.status_code}')
    except Exception as e:
        print(f'Failed to save {url} - {e}')

def download_facebook_images(url, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

    options = webdriver.FirefoxOptions()  # เปลี่ยนตรงนี้
    options.add_argument('-headless')      # และตรงนี้
    driver = webdriver.Firefox(options=options)
    driver.get(url)
    time.sleep(5)

    thumbnails = driver.find_elements(By.CSS_SELECTOR, 'img')

    count = 1
    for thumb in thumbnails:
        try:
            ActionChains(driver).move_to_element(thumb).click().perform()
            time.sleep(3)

            large_img = driver.find_element(By.CSS_SELECTOR, 'img[data-visualcompletion="media-vc-image"]')
            src = large_img.get_attribute('src')

            if src:
                src = src.replace("p320x320", "p1080x1080")
                save_image(src, folder, count)
                count += 1

            try:
                close_btn = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Close"]')
                close_btn.click()
                time.sleep(1)
            except:
                pass

        except Exception as e:
            print(f'Error at image {count}: {e}')
            continue

    driver.quit()

if __name__ == '__main__':
    url = 'https://www.facebook.com/share/p/16EPptXWsi/'  # URL สำหรับทดสอบ
    folder = 'downloaded'
    download_facebook_images(url, folder)  # เรียกใช้ฟังก์ชันใหม่