from werkzeug.utils import secure_filename
import json
import weaviate, os
from weaviate import EmbeddedOptions
import openai
from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, request

from flask import request, jsonify


_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ['OPENAI_API_KEY']

app = Flask(__name__)

def create_client():
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(),
        additional_headers={
            "X-OpenAI-Api-BaseURL": os.environ['OPENAI_API_BASE'],
            "X-OpenAI-Api-Key": openai.api_key,  # Replace this with your actual key
        }
    )

    if client.schema.exists("Question"):
       client.schema.delete_class("Question")
 
    class_obj = {
        "class": "Question",
        "vectorizer": "text2vec-openai",  # Use OpenAI as the vectorizer
        "moduleConfig": {
            "text2vec-openai": {
            "model": "ada",
            "modelVersion": "002",
            "type": "text",
            "baseURL": os.environ["OPENAI_API_BASE"]
            }
        }    
    }
    
    client.schema.create_class(class_obj)
    
    with client.batch.configure(batch_size=5) as batch:
        for i, d in enumerate(data):  # Batch import data
        
            print(f"importing question: {i+1}")
        
            properties = {
                "answer": d["Answer"],
                "question": d["Question"],
                "category": d["Category"],
            }
        
            batch.add_data_object(
                data_object=properties,
                class_name="Question"
            )
    return 
            


@app.route('/')
def index():
    return render_template('index.html')



@app.route('/upload_document', methods=['POST'])
def upload_document():
    global uploaded_file_path

    # Check if 'file' is in request.files
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    # Check if the file is empty
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    # Save the file to the current working directory
    upload_folder = os.getcwd()  # Get the current working directory
    uploaded_file_path = os.path.join(upload_folder, secure_filename(file.filename))
    file.save(uploaded_file_path)

    # Build the auto-merging index
    create_client()
    

    return jsonify({'success': True})





@app.route('/generate_response', methods=['POST'])
def generate_response():
    global uploaded_file_path

    # Check if a document has been uploaded
    if not uploaded_file_path or not os.path.isfile(uploaded_file_path):
        return jsonify({'error': 'Please upload a document first'})
    
    with open(uploaded_file_path, 'r') as file:
        data = json.load(file)
        
    question = request.form.get('question')
    alpha = float(request.form.get('alpha', 0.5))  # Get the alpha value, default to 0.5 if not provided

    response = (
        client.query
        .get("Question", ["question", "answer"])
        .with_hybrid(query=question, alpha=alpha)
        .with_limit(3)
        .do()
    )
    
    response_json = response.results

    return render_template('results.html', question=question, response=response_json)

if __name__ == '__main__':
    app.run(debug=True)