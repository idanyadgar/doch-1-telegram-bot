from typing import List, Callable
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException

class MSAuth:
    driver: WebDriver
    id_num: str
    ms_password: str

    def __init__(self, id_num: str, ms_password: str, idf_cookies: List[dict], ms_cookies: List[dict]):
        options = Options()
        options.headless = True

        self.driver = webdriver.Firefox(options=options, service=Service(log_path='/dev/null'))
        self.id_num = id_num
        self.ms_password = ms_password

        self.driver.get('https://login.microsoftonline.com/some404page')
        for cookie in ms_cookies:
            self.driver.add_cookie(cookie)

        self.driver.get("https://one.prat.idf.il/")
        for cookie in idf_cookies:
            self.driver.add_cookie(cookie)

    def _get_cookies(self, idf_window: str) -> (List[dict], List[dict]):
        self.driver.switch_to.window(idf_window)

        self.driver.switch_to.new_window()
        self.driver.get('https://login.microsoftonline.com/some404page')

        ms_cookies = self.driver.get_cookies()
        self.driver.close()

        self.driver.switch_to.window(idf_window)
        _ = WebDriverWait(self.driver, 10).until(EC.any_of(
            EC.presence_of_element_located((By.CLASS_NAME, "welcomeUser")),
            EC.presence_of_element_located((By.CLASS_NAME, "finishTitle"))))
        idf_cookies = self.driver.get_cookies()

        return idf_cookies, ms_cookies

    def login(self, get_otc_callback: Callable[[], str]) -> (List[dict], List[dict]):
        self.driver.get("https://one.prat.idf.il/login")
        element = WebDriverWait(self.driver, 10).until(EC.any_of(
            EC.presence_of_element_located((By.CLASS_NAME, "welcomeUser")),
            EC.presence_of_element_located((By.CLASS_NAME, "finishTitle")),
            EC.presence_of_element_located((By.NAME, "tz"))))

        if element.get_attribute("name") != "tz":
            return self._get_cookies(self.driver.current_window_handle)

        tz_elem = element

        current_handles = self.driver.window_handles
        idf_window = self.driver.current_window_handle

        tz_elem.send_keys(self.id_num)
        tz_elem.send_keys(Keys.ENTER)

        WebDriverWait(self.driver, 10).until(EC.new_window_is_opened(current_handles))
        self.driver.switch_to.window(self.driver.window_handles[len(current_handles)])

        try:
            password_elem = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "passwd")))
        except NoSuchWindowException:
            return self._get_cookies(idf_window)

        password_elem.send_keys(self.ms_password)
        password_elem.send_keys(Keys.ENTER)

        try:
            remember_mfa_elem = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "rememberMFA")))
            otc_elem = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "otc")))
        except NoSuchWindowException:
            return self._get_cookies(idf_window)

        remember_mfa_elem.click()
        while True:
            code = get_otc_callback()
            otc_elem.send_keys(code)

            otc_elem.send_keys(Keys.ENTER)

            try:
                _ = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, "idSpan_SAOTCC_Error_OTC")))
                otc_elem.clear()
            except TimeoutException:
                break
            except NoSuchWindowException:
                break

        try:
            dont_show_again_elem = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "DontShowAgain")))
        except NoSuchWindowException:
            return self._get_cookies(idf_window)

        dont_show_again_elem.click()
        dont_show_again_elem.send_keys(Keys.ENTER)

        WebDriverWait(self.driver, 10).until(EC.number_of_windows_to_be(1))

        return self._get_cookies(idf_window)

    def __del__(self):
        try:
            self.driver.quit()
        except Exception:
            pass
