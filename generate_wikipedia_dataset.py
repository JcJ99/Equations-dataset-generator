#!/usr/bin/python3

import requests
from requests_html import HTMLSession
import shutil
import cairosvg
from PIL import Image
import numpy as np
import os
import urllib.parse
import wikipedia
import sqlite3
import logging
from logging.handlers import TimedRotatingFileHandler

class database_exception(Exception):
    def __init__(self, strerr):
        self.strerr = strerr
    
    def __str__(self):
        return self.strerr

class RandomNoneException(Exception):
    def __init__(self, strerr):
        self.strerr = strerr

    def __str__(self):
        return self.strerr

logger = logging.getLogger(__name__)
handler = TimedRotatingFileHandler(filename="wikipedia_dataset.log", when="W0", interval=1)
formatter = logging.Formatter("%(asctime)s - %(message)s","%d-%m-%Y %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Descarga y trata todas las ecuaciones de una página de wikipedia
# y devuelve el número de ecuaciones descargadas.
def download_all_equations(wiki_link):
    session = HTMLSession()
    try:
        r = session.get(wiki_link)
    except requests.exceptions.MissingSchema:
        raise RandomNoneException("None type as wiki link")
    equations_obj = r.html.find("img.mwe-math-fallback-image-inline")
    folder_name = urllib.parse.unquote(wiki_link).split("/")[-1]
    if equations_obj:
        try:
            os.mkdir(folder_name)
            eq_urls = [eq.attrs["src"] for eq in equations_obj]
            eqs_latex = [eq.attrs["alt"] for eq in equations_obj]
            for eq_url, eq_latex in zip(eq_urls, eqs_latex):
                eq_img_r = requests.get(eq_url, stream=True)
                if eq_img_r.status_code == 200:
                    eq_img_r.raw.decode_content = True
                    eq_path = folder_name + "/" + eq_url.split("/")[-1]
                    with open(eq_path + ".svg", "wb") as f:
                        shutil.copyfileobj(eq_img_r.raw, f)
                    cairosvg.svg2png(url=eq_path + ".svg", write_to=eq_path + ".png")
                    eq_img = Image.open(eq_path + ".png")
                    data = np.array(eq_img)
                    eq_img.close()
                    mask = np.less(data[:,:,3], 60)
                    data[:,:,:][mask] = [255, 255, 255, 255]
                    eq_img_final = Image.fromarray(data)
                    eq_img_final.save(eq_path + ".png")
                    with open(eq_path + ".txt", "w") as f:
                        f.write(eq_latex)
        except FileExistsError:
            print("Ya existe un directorio con el nombre de la página de Wikipedia Introducido")

        svgs = [os.path.join(os.getcwd(), folder_name, file) for file in os.listdir(os.path.join(os.getcwd(), folder_name)) if file.endswith(".svg")]
        for svg in svgs:
            os.remove(svg)

    return len(equations_obj)

def get_random_wiki():
    page_name = wikipedia.random(1)
    try:
        page_link = wikipedia.page(page_name).url
        return page_link, page_name
    except wikipedia.exceptions.DisambiguationError:
        return None, None
    except wikipedia.exceptions.PageError:
        return None, None

def safe_database_connect():
    database = sqlite3.connect("wikipedia_dataset.db")
    try:
        database.execute("""CREATE TABLE wiki_pages (
                            name TEXT PRIMARY KEY,
                            visited INT DEFAULT 1,
                            url TEXT NOT NULL);""")
        return database
    except sqlite3.OperationalError as e:
        if str(e) == "table wiki_pages already exists":
            return database
        else: 
            raise    

def add_new_pages_to_database(database, source_wiki_name):
    wiki_page = wikipedia.page(source_wiki_name)
    new_wikis_name = wiki_page.links
    choosen_names = np.random.choice(new_wikis_name, size=min(len(new_wikis_name), 40), replace=False)
    choosen_names = list(choosen_names)
    new_wikis_link = []
    for name in choosen_names:
        try:
            new_wikis_link.append(wikipedia.page(name).url)
        except KeyError as e:
            choosen_names.remove(name)
        except wikipedia.exceptions.DisambiguationError as e:
            while True:
                try:
                    wiki_page = wikipedia.page(np.random.choice(e.options))
                    new_wikis_link.append(wiki_page.url)
                    index = choosen_names.index(name)
                    choosen_names[index] = wiki_page.title
                    break
                except wikipedia.exceptions.DisambiguationError:
                    continue
                except wikipedia.exceptions.PageError:
                    continue
        except wikipedia.exceptions.PageError:
            choosen_names.remove(name)

    data = [(wiki_name, 0, wiki_link) for wiki_name, wiki_link in zip(choosen_names, new_wikis_link)]
    c = database.cursor()
    try:
        c.executemany("INSERT INTO wiki_pages(name, visited, url) VALUES(?,?,?);", data)
    except sqlite3.IntegrityError as e:
        if str(e) == "UNIQUE constraint failed: wiki_pages.name":
            qstr = "SELECT name FROM wiki_pages WHERE name=? " + ("OR name=?" * (len(choosen_names) - 1) + ";")
            already_saved_names = database.execute(qstr, choosen_names)
            already_saved_names = [already_saved_name[0] for already_saved_name in already_saved_names]
            aux_list = [el[0] for el in data]
            for name in already_saved_names:
                index = aux_list.index(name)
                del data[index]
                del aux_list[index]
        else:
            raise
    database.commit()
    return len(data)

def add_visited_page_to_database(database, source_wiki_name):
    c = database.execute("SELECT name FROM wiki_pages WHERE name=(?);", [source_wiki_name])
    if len(c.fetchall()) == 0:
        wiki_page = wikipedia.page(source_wiki_name)
        wiki_link = wiki_page.url
        database.execute("INSERT INTO wiki_pages(name, visited, url) VALUES(?,?,?);", (source_wiki_name, 1, wiki_link))
    else:
        database.execute("UPDATE wiki_pages SET visited=1 WHERE name=(?)", [source_wiki_name])
    database.commit()

def get_next_page(database):
    c = database.execute("SELECT * FROM wiki_pages WHERE visited=0 LIMIT 1;")
    next_page_tup = c.fetchone()
    return next_page_tup

def main():
    try:
        eq_to_download = int(input("Number of equations to get: "))
        seed = input("Wikipedia page name from where to start (Blank for random start or continue): ")
        if seed:
            page = wikipedia.page(seed)
            database = safe_database_connect()
            database.execute("INSERT INTO wiki_pages(name, visited, url) VALUES(?,?,?)", (page.title, 0, page.url))
        else:
            database = safe_database_connect()
        downloaded_eq = 0
        # Add all links in a wiki page to the search directory
        while downloaded_eq < eq_to_download:
            if next_page := get_next_page(database):
                eq_num = download_all_equations(next_page[2])
                downloaded_eq += eq_num
                logstr = f"Visited: {next_page[0]} - {eq_num} equations added."
                if eq_num > 0:
                    added_to_db = add_new_pages_to_database(database, next_page[0])
                    logstr += f" {added_to_db} wiki pages added to db."
                add_visited_page_to_database(database, next_page[0])
                logger.info(logstr)
            else:
                next_page_link, next_page_name = get_random_wiki()
                try:
                    eq_num = download_all_equations(next_page_link)
                except RandomNoneException:
                    continue
                downloaded_eq += eq_num
                logstr = f"Visited: {next_page_name} - {eq_num} equations added."
                if eq_num > 0:
                    add_new_pages_to_database(database, next_page_name)
                    logstr += f" {added_to_db} wiki pages added to db."
                add_visited_page_to_database(database, next_page_name)
                logger.info(logstr)

        database.close()
    except KeyboardInterrupt:
        print()

if __name__ == "__main__":
    main()