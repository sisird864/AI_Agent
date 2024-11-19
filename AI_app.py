from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
from os import environ
from dotenv import load_dotenv
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = environ["OPENAI_API_KEY"]

app = Flask(__name__)

# Initialize Phoenix only if needed (you can comment these out if causing issues)
try:
    import phoenix as px
    from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
    from phoenix.otel import register
    
    # Set environment variable to change default port if needed
    environ["PHOENIX_OTEL_EXPORTER_OTLP_ENDPOINT"] = "localhost:4318"  # Use different port
    
    session = px.launch_app()
    tracer_provider = register()
    LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
    phoenix_enabled = True
except Exception as e:
    print(f"Phoenix initialization skipped: {e}")
    phoenix_enabled = False

# Initialize AI components
def initialize_ai():
    llm = OpenAI(model="gpt-4")
    
    try:
        # Try to load existing indices
        storage_context = StorageContext.from_defaults(persist_dir="./storage/sorge")
        sorge_index = load_index_from_storage(storage_context)

        storage_context = StorageContext.from_defaults(persist_dir="./storage/fischer")
        fischer_index = load_index_from_storage(storage_context)

    except:
        # If loading fails, create new indices
        sorge_docs = SimpleDirectoryReader(
            input_files=["./10k/rapa_sorge_2014.pdf"]
        ).load_data()
        fischer_docs = SimpleDirectoryReader(
            input_files=["./10k/rapa_fischer_2015.pdf"]
        ).load_data()

        sorge_index = VectorStoreIndex.from_documents(sorge_docs, show_progress=True)
        fischer_index = VectorStoreIndex.from_documents(fischer_docs, show_progress=True)

        sorge_index.storage_context.persist(persist_dir="./storage/sorge")
        fischer_index.storage_context.persist(persist_dir="./storage/fischer")

    # Create query engines
    sorge_engine = sorge_index.as_query_engine(similarity_top_k=3, llm=llm)
    fischer_engine = fischer_index.as_query_engine(similarity_top_k=3, llm=llm)

    # Set up tools
    query_engine_tools = [
        QueryEngineTool(
            query_engine=sorge_engine,
            metadata=ToolMetadata(
                name="sorge_10k",
                description="Provides information about Rapamycin from Sorge paper."
            ),
        ),
        QueryEngineTool(
            query_engine=fischer_engine,
            metadata=ToolMetadata(
                name="fischer_10k",
                description="Provides information about Rapamycin from Fischer paper."
            ),
        ),
    ]

    # Create agent
    return ReActAgent.from_tools(
        query_engine_tools,
        llm=llm,
        verbose=True,
        max_turns=10,
    )

# Initialize the AI agent
agent = initialize_ai()

def get_ai_response(question):
    """Get response from AI agent"""
    try:
        response = agent.chat(question)
        return str(response)
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return "I apologize, but I encountered an error processing your question."

@app.route("/voice", methods=['POST'])
def voice():
    response = VoiceResponse()
    
    gather = response.gather(
        input='speech',
        action='/handle_response',
        method='POST',
        language='en-US',
        speechTimeout='auto'
    )
    gather.say("Hello, please ask your question about Rapamycin.")
    
    return str(response)

@app.route("/handle_response", methods=['POST'])
def handle_response():
    response = VoiceResponse()
    user_question = request.values.get('SpeechResult', '')
    
    if user_question:
        # Get AI response
        ai_response = get_ai_response(user_question)
        response.say(ai_response)
    else:
        response.say("I didn't catch that. Please call again and try your question.")
    
    return str(response)

if __name__ == "__main__":
    app.run(debug=True)