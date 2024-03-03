from flask import Flask, request, jsonify, render_template, redirect, url_for
from elasticsearch import Elasticsearch
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from bson.objectid import ObjectId


client = MongoClient('mongodb://localhost:27017/')
db = client['article_database']
# Select the collection within the database
collection = db['articles']


app = Flask(__name__)


def save_to_mongodb(data):
    try:
        # Insert the data into the collection
        collection.insert_one(data)
        print("Data saved to MongoDB")
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")



def scrape_article_details(query):
    url = f'https://dergipark.org.tr/tr/search?q={query}&section=articles'
    response = requests.get(url)
    if response.status_code != 200:
        print("Error fetching the page")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    article_links=[]
    makale_linkler=soup.select('h5',class_='card-title')
    for link in makale_linkler:
        link=link.find('a')
        
        article_links.append(link['href'])

    for link in article_links[:11]:
        print(link)
        article_page = requests.get(link)
        article_soup = BeautifulSoup(article_page.content, 'html.parser')

        title = article_soup.find('h3',class_='article-title').text.strip()
        detail_elements = article_soup.select("table.record_properties.table tr")

        authors = []
        section, publication_date, publisher_name = "", "", ""
        for tr in detail_elements:
            property_name = tr.find('th').text.strip()
            if property_name == "Yazarlar":
                authors = [author.text.strip().split('\n')[0] for author in tr.select('td p')]
            elif property_name == 'Bölüm':
                section = tr.find('td').text.strip()
            elif property_name == 'Yayımlanma Tarihi':
                publication_date = tr.find('td').text.strip()

        # publisher_name = article_soup.select_one('div.kt-portlet__body.overflow-auto').text.strip()
        abstract = article_soup.find('meta', {"name": "citation_abstract"})['content'] if article_soup.find('meta', {"name": "citation_abstract"}) else ""
        keywords = [keyword.strip() for keyword in article_soup.select_one('div.article-keywords.data-section p').text.split(',')]
        references = [ref['content'] for ref in article_soup.find_all('meta', {'name': 'citation_reference'})]
        citation_count = len(references)
        doi = article_soup.select_one('a.doi-link')['href'] if article_soup.select_one('a.doi-link') else ''
        download_link = "https://dergipark.org.tr" + article_soup.select_one('a[title="Makale PDF linki"]')['href'] if article_soup.select_one('a[title="Makale PDF linki"]') else ''

        print(f"Title: {title}")
        print(f"Authors: {', '.join(authors)}")
        print(f"Section: {section}")
        print(f"Publication Date: {publication_date}")
        # print(f"Publisher Name: {publisher_name}")
        print(f"Abstract: {abstract}")
        print(f"Keywords: {', '.join(keywords)}")
        print(f"References Count: {citation_count}")
        print(f"DOI: {doi}")
        print(f"Download Link: {download_link}")
        print("-" * 100)

        data = {
            "title": title,
            "authors": authors,
            "section": section,
            "publication_date": publication_date,
            # "publisher_name": publisher_name,
            "query": query,
            "abstract": abstract,
            "keywords": keywords,
            "references_count": citation_count,
            "doi": doi,
            "download_link": download_link,
            "article_link": link
        }
        
        # Save the data to MongoDB
        save_to_mongodb(data)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query', '')
    if query:
        scrape_article_details(query)
        articles = collection.find({"query": query})
        return render_template('results.html', query=query, articles = articles)
    else:
        return render_template('index.html', error="Arama terimi boş olamaz.")

@app.route('/article/<article_id>')
def article_detail(article_id):
    # MongoDB'den ObjectId kullanarak makaleyi bul
    article = collection.find_one({'_id': ObjectId(article_id)})
    if article:
        return render_template('article_detail.html', article=article)
    else:
        return redirect(url_for('index'))

    
    


if __name__ == '__main__':
    app.run(debug=True)
