import os
import time
import csv
import random
from datetime import datetime
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from dotenv import load_dotenv


load_dotenv()
UserName = os.getenv('user_name')
PassWrd = os.getenv('login_code')

def login(driver):
    loglink = "https://www.instagram.com/accounts/login/"
    username = UserName
    password = PassWrd

    driver.get(loglink)
    driver.implicitly_wait(3)

    usernameh = driver.find_element(By.NAME, 'username')
    usernameh.send_keys(username)

    passwordh = driver.find_element(By.NAME, 'password')
    passwordh.send_keys(password)

    driver.implicitly_wait(3)
    passwordh.send_keys(Keys.ENTER)
    time.sleep(8)

def get_post_links(driver, profile_url, max_scroll_attempts=300):
    maxposts = 3469
    driver.get(profile_url)
    time.sleep(5)

    post_links = set()  # Используйте набор, чтобы избежать дубликатов
    pbar = tqdm(total=maxposts)  # Инициализировать индикатор выполнения

    for _ in range(max_scroll_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(4, 6))

        # Извлекать ссылки на публикации
        soup = bs(driver.page_source, 'html.parser')
        links = soup.find_all('a')
        new_post_links = set([link['href'] for link in links if '/p/' in link['href']])
        post_links.update(new_post_links)

        # Индикатор выполнения обновления
        pbar.update(len(new_post_links))

        if len(new_post_links) == 0:
            break  # Прервать, если новые ссылки не найдены

    pbar.close()  # Закрыть индикатор выполнения
    return [post_link[3:-1] for post_link in post_links]

def get_comments(driver, postlink, post_id):
    # Откройте пост в Instagram
    post_url = f'https://www.instagram.com/p/{postlink}/'
    driver.get(post_url)
    time.sleep(10)


    #Проанализируйте загруженную страницу
    soup = bs(driver.page_source, 'html.parser')

    # Найдите все разделы комментариев
    comment_divs = soup.find_all('div', class_='x9f619 xjbqb8w x78zum5 x168nmei x13lgxp2 x5pf9jr xo71vjh x1uhb9sk x1plvlek xryxfnj x1iyjqo2 x2lwn1j xeuugli x1q0g3np xqjyukv x1qjc9v5 x1oa3qoh x1nhvcw1')

    # Извлеките комментарии, лайки и даты из каждого раздела
    table = []
    for div in comment_divs:
        spans = div.find_all('span', class_='x1lliihq x1plvlek xryxfnj x1n2onr6 x193iq5w xeuugli x1fj9vlw x13faqbe x1vvkbs x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x x1i0vuye xvs91rp xo1l8bm x5n08af x10wh9bi x1wdrske x8viiok x18hxmgj')
        comment = spans[-1].text if spans else ''
        likes_count_span = div.find('span', class_='x1lliihq x193iq5w x6ikm8r x10wlt62 xlyipyv xuxw1ft')
        likes_count = likes_count_span.text if likes_count_span and (likes_count_span.text.endswith('like') or likes_count_span.text.endswith('likes')) else '0 likes'
        comment_date_time = div.find('time', class_='x1ejq31n xd10rxx x1sy0etr x17r0tee x1roi4f4 xexx8yu x4uap5 x18d9i69 xkhd6sd x1n2onr6')
        comment_date = comment_date_time['title'] if comment_date_time else ''
        table.append([post_id, comment, likes_count, comment_date])

    return table[1:]

def full_comments(driver, filename):
    # Полный список комментариев
    comment_list = []

    # Получите ссылки на публикации, чтобы просмотреть каждый из них
    with open(filename, 'r') as f:
        post_links = [line.strip() for line in f]

    id_counter = 1  # Инициализируйте счетчик
    for postlink in post_links:
        comments = get_comments(driver, postlink, id_counter)

        
        # если подключение к Интернету потеряно, верните то, что у нас есть на данный момент
        if not comments:
            return comment_list
        
        comment_list.append((id_counter, postlink, comments))
        id_counter += 1  # Увеличьте значение счетчика

    return comment_list

def WriteComments(comment_list, output_filename):
    with open(output_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Post ID', 'Comment', 'Likes Count', 'Comment Date'])
        
        for post_id, postlink, comments in comment_list:
            for comment in comments:
                # Проверьте, не является ли строка даты пустой
                if comment[3]:
                    # Преобразуйте строку даты в объект datetime
                    date_obj = datetime.strptime(comment[3], "%b %d, %Y")
                    # Отформатируйте объект datetime в строку в нужном формате
                    formatted_date_str = date_obj.strftime("%Y-%m-%d")
                else:
                    formatted_date_str = ''
                likes_count = comment[2].split()[0]
                writer.writerow([comment[0], comment[1], likes_count, formatted_date_str])


driver = webdriver.Chrome()
print('Logging in...')
login(driver)
print('Loading webdriver')

# profile_url = 'https://www.instagram.com/potus/'  # replace with the profile you want
# print('Getting post links...')
# post_links = get_post_links(driver, profile_url)
# with open('post_links.csv', 'w', newline='') as f:
#     writer = csv.writer(f)
#     for link in post_links:
#         writer.writerow([link])
# print('POSTS READY')
# print('Getting comments')

comment_list = full_comments(driver, 'post_links.csv')
print("Comments list is ready...\nLoading to csv file")
WriteComments(comment_list, 'full_comments.csv')
print("SUCCESS")

# Функция для определения тональности комментария
def classify_sentiment(comment):
    positive_words = ['thank', 'love', 'beautiful', 'great', 'respect', 'bless', '😍', '👏', '😊', '🙏']
    negative_words = ['😔', '💔', 'tragic', 'laughing stock', 'KKK', 'retire']

    # Проверка наличия позитивных слов в комментарии
    for word in positive_words:
        if word in comment.lower():
            return 'positive'

    # Проверка наличия негативных слов в комментарии
    for word in negative_words:
        if word in comment.lower():
            return 'negative'

    return None  # Нейтральность удалена

# Загрузка данных из CSV файла
with open('ready_comments.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    comments_with_sentiment = []

    # Обработка комментариев
    for row in reader:
        sentiment = classify_sentiment(row['Comment'])
        if sentiment:  # Проверка на None, чтобы не включать нейтральные комментарии
            row['Sentiment'] = sentiment
            row['Likes Count'] = int(row['Likes Count'].replace(',', '')) + 1  # Удаляем запятые и увеличиваем 'Likes Count' на 1
            comments_with_sentiment.append(row)

# Запись комментариев с сентиментом в новый CSV файл
with open('comments_with_sentiment.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Post ID', 'Comment', 'Sentiment', 'Likes Count', 'Comment Date']  # Добавляем 'Post ID'
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(comments_with_sentiment)
