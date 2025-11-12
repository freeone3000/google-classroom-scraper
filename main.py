from os import getenv
from pathlib import Path
from time import sleep

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

# the following were updated on 2025-11-12
CLASS_CLASS_NAME: str = "ScpeUc Vu2fZd XwD7Ke"
LESSON_CLASS_NAME: str = "Vu2fZd Cx437e"
MATERIAL_CLASS_NAME: str = "A6dC2c QDKOcc UtdKPb U0QIdc"

class GCScraper:
    def __init__(
            self, email, password, downloadDirectory
    ):
        self.email = email
        self.password = password

        self.prefs = {
            "download.default_directory": downloadDirectory,
            'download.directory_upgrade': True
        }
        self.options = webdriver.ChromeOptions()
        self.options.add_experimental_option("prefs", self.prefs)

        self.service = Service()
        self.driver = uc.Chrome(
            service=self.service, options=self.options
        )
        self.driver.maximize_window()

        self.LOGIN_URL = r"https://accounts.google.com/v3/signin/identifier"
        self.LOGIN_URL += r"?continue=https%3A%2F%2Fclassroom.google.com"
        self.LOGIN_URL += r"&passive=true&flowName=GlifWebSignIn"
        self.LOGIN_URL += r"&flowEntry=ServiceLogin&theme=glif"
        self.LOGIN_URL += r"&dsh=S-469499581%3A1699752740709820"

    def login(self):
        try:
            self.driver.get(self.LOGIN_URL)

            self.driver.implicitly_wait(15)

            self.driver.find_element(
                "xpath", '//*[@id="identifierId"]'
            ).send_keys(self.email)
            self.driver.find_elements(
                "xpath", '//*[@id="identifierNext"]'
            )[0].click()

            sleep(2)

            if self.password != "%%USE PASSKEY%%":
                self.driver.find_element(
                    "xpath", '//*[@id="password"]/div[1]/div/div[1]/input'
                ).send_keys(self.password)
                self.driver.find_elements(
                    "xpath", '//*[@id="passwordNext"]'
                )[0].click()

            sleep(5)

            self.gcURL = self.driver.current_url

            print("Login Successful")
        except Exception as e:
            print("Login Failed")
            print("Error:", e)

    def getDriver(self):
        return self.driver

    def findCourse(self, courseTitle):
        try:
            sleep(10)

            course = self.driver.find_element(
                "xpath", f'//div[contains(text(), "{courseTitle}") and @class="{CLASS_CLASS_NAME}"]'
            )
            self.courseTitle = course.text
            course.click()

            classwork = self.driver.find_element(
                "xpath", '//a[contains(text(), "Classwork")]'
            )
            classwork.click()

            print("Course Found -", self.courseTitle)
        except Exception as e:
            print("Course Not Found")
            print("Error:", e)

    def getLinks(self):
        sleep(10)

        links = []

        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

        sleep(5)

        viewMore = self.driver.find_element(
            "xpath", "//span[contains(text(), 'View more') and @aria-hidden='true']"
        )

        while viewMore:
            self.driver.execute_script("arguments[0].click()", viewMore)

            sleep(2)

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            sleep(1)

            viewMore = self.driver.find_element(
                "xpath", "//span[contains(text(), 'View more') and @aria-hidden='true']"
            )

        posts = self.driver.execute_script(
            f"return document.getElementsByClassName('{LESSON_CLASS_NAME}')"
        )

        print(f"Found {len(posts)} Posts")

        self.driver.implicitly_wait(5)

        for post in posts:
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", post
            )
            self.driver.execute_script("arguments[0].click();", post)

        sleep(5)

        materials = self.driver.execute_script(
            f"return document.getElementsByClassName('{MATERIAL_CLASS_NAME}');"
        )

        print(f"Found {len(materials)} Materials")

        self.driver.implicitly_wait(5)

        for material in materials:
            anchors = material.find_elements(By.TAG_NAME, "a")

            for anchor in anchors:
                links.append(anchor.get_attribute("href"))

        return self.courseTitle, links

    def close(self):
        self.driver.close()


class Downloader:
    def __init__(self, courseTitle, links, driver):
        self.courseTitle = courseTitle
        self.links = links
        self.driver = driver

    def classifyLinks(self):
        self.driveLinks = [link for link in self.links if link.split(
            "/")[2] == "drive.google.com"]
        self.otherLinks = [
            link for link in self.links if link not in self.driveLinks
        ]

    def download(self, downloadDirectory):
        otherLinks = '\n'.join(self.otherLinks)

        directory = Path(downloadDirectory)
        if not directory.exists():
            directory.mkdir(parents=False, exist_ok=False)

        file = Path(f"{downloadDirectory}/{self.courseTitle}.txt")
        file.touch(exist_ok=True)
        file.write_text(otherLinks)

        print("Saved Other Links\n")
        print("Starting Download...\n")

        for link in self.driveLinks:
            print("Downloading:", link)

            self.driver.get(
                f"https://drive.google.com/uc?export=download&id={link.split('/')[5]}"
            )

            sleep(5)

            print("Downloaded\n")


if __name__ == "__main__":
    load_dotenv()

    course_list = list(
        map(lambda x: x[1:-1], getenv("COURSE_LIST")[1:-1].split(", "))
    )

    print(course_list)

    email = getenv("EMAIL")
    password = getenv("PASSWORD")
    downloadDirectory = getenv("DOWNLOAD_DIRECTORY")

    gcscraper = GCScraper(
        email=email,
        password=password,
        downloadDirectory=downloadDirectory
    )

    gcscraper.login()
    driver = gcscraper.getDriver()

    for course in course_list:
        print(course)

        gcscraper.findCourse(courseTitle=course)

        ct, links = gcscraper.getLinks()

        downloader = Downloader(courseTitle=ct, links=links, driver=driver)
        downloader.classifyLinks()
        downloader.download(downloadDirectory=downloadDirectory)

        driver.get(gcscraper.gcURL)

    print("Waiting for any remaining downloads to finish...")

    sleep(300)

    print("Done")

    gcscraper.close()
