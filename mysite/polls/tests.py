from selenium import webdriver
#貯列等待
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.keys import Keys

from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.action_chains import ActionChains

import time
import random
options = Options()
options.chrome_executable_path = "C:/Users/CHBI965/Desktop/123/chromedriver-win64/chromedriver.exe"



driver=webdriver.Chrome(options=options)
#driver.get("https://translate.google.com/?hl=zh-TW")
driver.get("http://localhost:8000/polls/")
for i in range (20000):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "filterBtn"))
    )
    findsearch=driver.find_element("xpath",'//*[@id="filterBtn"]')
    findsearch.click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "targetDropdown"))
    )
    targetsearch=driver.find_element("xpath",'//*[@id="targetDropdown"]')
    targetsearch.click()

    wait = WebDriverWait(driver, 10)
    target_element = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="targetDropdownMenu"]/li[5]/input')))

    random_number = random.randint(1, 5)
    if random_number == 1:
        target_1=driver.find_element("xpath",'//*[@id="selectAllCheckbox"]').click()
    elif random_number == 2:
        target_2=driver.find_element("xpath",'//*[@id="targetDropdownMenu"]/li[2]/input').click()
    elif random_number == 3:
        target_3=driver.find_element("xpath",'//*[@id="targetDropdownMenu"]/li[3]/input').click()
    elif random_number == 4:
        target_4=driver.find_element("xpath",'//*[@id="targetDropdownMenu"]/li[4]/input').click()
    elif random_number == 5:
        target_5=driver.find_element("xpath",'//*[@id="targetDropdownMenu"]/li[5]/input').click()

    pop=driver.find_element("xpath",'//*[@id="popupContent"]/h2').click()

    groupsearch=driver.find_element("xpath",'//*[@id="groupDropdown"]')
    groupsearch.click()

    wait = WebDriverWait(driver, 10)
    group_element = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="groupDropdownMenu"]/li[3]/input')))

    random_number = random.randint(1, 3)
    if random_number == 1:
        group_1=driver.find_element("xpath",'//*[@id="selectAllGroupsCheckbox"]').click()
    elif random_number == 2:
        group_2=driver.find_element("xpath",'//*[@id="groupDropdownMenu"]/li[2]/input').click()
    elif random_number == 3:
        group_3=driver.find_element("xpath",'//*[@id="groupDropdownMenu"]/li[3]/input').click()

    pop=driver.find_element("xpath",'//*[@id="popupContent"]/h2').click()

    finalsearch=driver.find_element("xpath",'//*[@id="applyFilterBtn"]')
    actions = ActionChains(driver)
    actions.move_to_element(finalsearch).double_click().perform()

    '''
    action.move_to_element(finalsearch).click_and_hold
    action.release()
    action.perform()
    '''
    time.sleep(5)
driver.quit()