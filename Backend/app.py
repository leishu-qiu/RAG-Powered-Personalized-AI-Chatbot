import os
from langchain_community.document_loaders import TextLoader
from langchain.memory import ConversationBufferMemory
from werkzeug.utils import secure_filename

from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from flask import Flask, render_template, request, jsonify,g
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from flask_cors import CORS
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain.docstore.document import Document


app = Flask(__name__)
CORS(app,supports_credentials=True) 
app.secret_key = '123456'  


# LangChain Chat Model setup
os.environ["OPENAI_API_KEY"] = ""
os.environ['PINECONE_API_KEY'] = ""

llm = ChatOpenAI(
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
    model='gpt-3.5-turbo'
)

# Embedding model
embed_model = OpenAIEmbeddings(model="text-embedding-ada-002")

#update
index_name = "chatbot"
vectorstore = PineconeVectorStore(index_name=index_name, embedding=embed_model)

memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True,output_key='answer')
conversation_chain = ConversationalRetrievalChain.from_llm(
    return_source_documents = True,
    llm=llm,
    chain_type="stuff",
    retriever= vectorstore.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.9}),
    memory=memory
)
sources = []
selected_sources = []
use_filter = False
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc','docx'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def handle_query():
    global use_filter
    user_input = request.json['query']
    # print(session.get('selected_sources'))
    # print(session.get('use_filter'))
    # use_filter = session.get('use_filter')
    # print(use_filter)
    # if 'use_filter' not in g:
    #     g.use_filter = False
    if use_filter:
        print("use_filter")
        answer,references = chat_with_filter(user_input) if user_input else 'No query provided.'
    else:
        print("no_filter")
        print(use_filter)
        answer,references = chat(user_input) 
    return jsonify({'answer': answer,'references':references})

@app.route('/selective', methods=['POST'])
def handle_selective_sources():
    global use_filter
    global selected_sources
    selected_sources = request.json['selectedSources']
    # if 'use_filter' not in g:
    #     g.use_filter = False
    # if 'selected_sources' not in g:
    #     g.use_filter = False
    use_filter = True
    # g.selected_sources = selected_sources  
    print(selected_sources)  
    return jsonify({'message': 'Sources set successfully'})

@app.route('/sources', methods=['GET'])
def return_sources():
    global sources
    # if 'sources' not in session:
    #     print(session.get('sources',[]))
    #     session['sources'] = []
    return jsonify({'sources': sources})

@app.route('/selective_off', methods=['POST'])
def disable_filtering():
    global selected_sources
    global use_filter
    # Clear specific session variables
    # if 'selected_sources' in session:
    #     del session['selected_sources']
    selected_sources = []
    print("filter_off")
    # Alternatively, disable filtering without deleting variables
    # session['use_filter'] = False
    use_filter = False
    return jsonify({'message': 'Selective filtering disabled'})

# @app.route('/selective_delete', methods=['POST'])
# def handle_selective_deletion():
#     selected_sources = request.get_json().get('selectedSources',[])
#     if not selected_sources:
#         return jsonify({'message': 'No sources provided for deletion'}), 400
#     filters= {'source': {'$in': selected_sources}}
#     try:
#         # Call the delete method with the filter
#         vectorstore.delete(filter=filters)
#         return jsonify({'message': 'Requested sources have been deleted'}), 200
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def handle_upload():
    global sources
    if 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('./', filename)
            file.save(file_path)
            update_document_store(file_path, file.filename.rsplit('.', 1)[1].lower())
            # if 'sources' not in session:
            #     session['sources'] = []
            sources.append(file_path)
            # session['sources'].append(file_path)  # Store the filename
            return jsonify({'message': 'File uploaded and processed successfully.'})
            # return jsonify({'sources': session['sources']})
    return jsonify({'message': 'Invalid file or no file uploaded.'})

@app.route('/url', methods=['POST'])
def scrape_url():
    global sources
    # method expects a JSON payload with a URL
    if not request.json or 'url' not in request.json:
        return jsonify({'message': 'No URL provided'}), 400

    url = request.json['url']
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        # text = soup.get_text()
        text = soup.get_text(strip=True)
        chunks = chunk_text(text)
        #update
        domain_name = get_domain(url)
        # if 'sources' not in session:
        #     session['sources'] = []
        # session['sources'].append(domain_name) 
        sources.append(domain_name)
        metadatas = [{'source': domain_name} for _ in chunks]
        vectorstore.add_texts(chunks, metadatas)
        return jsonify({'content': text[:500]})  
    except requests.RequestException as e:
        return jsonify({'message': 'Failed to retrieve the URL', 'error': str(e)})

# @app.route('/urlnew', methods=['POST'])
# def scrape_url_new():
#     # This method expects a JSON payload with a URL
#     if not request.json or 'url' not in request.json:
#         return jsonify({'message': 'No URL provided'}), 400

#     url = request.json['url']
#     try:
#         response = requests.get(url)
#         soup = BeautifulSoup(response.content, 'html.parser')
#         # text = soup.get_text()
#         text = soup.get_text(strip=True)
#         # chunks = chunk_text(text)
#         #update
#         domain_name = get_domain(url)
#         doc = [Document(page_content=text, metadata = {'source' : 'new'})]
#         # if 'sources' not in session:
#         #     session['sources'] = []
#         # session['sources'].append(domain_name) 
#         sources.append(domain_name)
#         text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200,    separator="\n")
#         chunks = text_splitter.split_documents(doc)
#         print(len(chunks))
#         vectorstore.add_documents(chunks)
#         # Optionally, process the text or return a portion of it
#         return jsonify({'content': text[:500]})  # Return first 500 characters of the text
#         # return jsonify({'sources': session['sources']})
#     except requests.RequestException as e:
#         return jsonify({'message': 'Failed to retrieve the URL', 'error': str(e)})


def get_domain(url):
    """ Extract the domain name from a URL. """
    parsed_uri = urlparse(url)
    full_path = f'{parsed_uri.netloc}{parsed_uri.path}'
    return full_path.rstrip('/') 

def chunk_text(text, chunk_size=1000):
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence + '. '
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + '. '
    #TODO: overlap
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def update_document_store(file_path, ext):
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    if(ext == 'txt'):
        loader = TextLoader(file_path=file_path, encoding="utf-8")
    elif(ext == 'pdf'):
        loader = PyPDFLoader(file_path=file_path)
    elif(ext == 'doc' or ext == 'docx'):
        print(file_path)
        # loader = Docx2txtLoader(file_path = file_path)
        loader = UnstructuredWordDocumentLoader(file_path=file_path)
    data = loader.load_and_split(text_splitter=text_splitter)
    # chunks = text_splitter.split_documents(data)
    # pages = loader.load_and_split()
    vectorstore.add_documents(data)


def chat(query):
    result = conversation_chain({"question": query})
    references = [doc.page_content for doc in result['source_documents']]
    # print("chat without filter")
    answer = result["answer"]
    return answer,references

def chat_with_filter(query):
    # selected_sources = session.get('selected_sources',[])
    global selected_sources
    filters = {"source": {"$in": selected_sources}}
    print(filters)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        return_source_documents = True,
        llm=llm,
        chain_type="stuff",
        retriever= vectorstore.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.9, "filter":filters}),
        memory=memory
    )   
    result = conversation_chain({"question": query})
    answer = result["answer"]
    references = [doc.page_content for doc in result['source_documents']]
    return answer,references

if __name__ == '__main__':
    app.run(port = 3000, debug=True)