from selenium import webdriver

def test_selenium_setup():
    # driver = webdriver.Chrome('/path/to/chromedriver')
    driver = webdriver.Chrome()  # If the ChromeDriver is in your PATH
    driver.get('https://www.google.com')
    print(driver.title)
    driver.quit()

if __name__ == "__main__":
    test_selenium_setup()
