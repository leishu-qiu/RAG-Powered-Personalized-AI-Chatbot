# ideal place for the bulk of logic including loading and preprocessing data, and splitting it into chunks.
import openai
import os
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from config import get_api_key
from data_loader import DataLoader


file = '../CSCI2270_Info.txt'

data_loader = DataLoader(file)
data = data_loader.load_data()
preprocessed_data = data_loader.preprocess_data(data)

# set api key
get_api_key()

with open('CSCI2270_Info.txt', 'r', encoding='utf-8') as file:
    file_contents = file.read()

txt_file_path = 'CSCI2270_Info.txt'

with open(txt_file_path, 'r', encoding='utf-8') as file:
    data = file.read()

def split_text_into_chunks(text, chunk_size=1000, chunk_overlap=200):
    chunks = []
    start = 0
    while start + chunk_size <= len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap 
    
    if start < len(text):
        chunks.append(text[start:])
    
    return chunks

data_chunks = split_text_into_chunks(data, chunk_size=1000, chunk_overlap=200)

embeddings = OpenAIEmbeddings()