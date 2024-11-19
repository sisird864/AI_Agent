from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import os
from typing import Optional

# Initialize Flask app
app = Flask(__name__)

# Twilio credentials - replace with your actual credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN")

def get_agent_response(query: str) -> Optional[str]:
    """
    Get response from your existing agent chat implementation
    Returns None if there's an error
    """
    try:
        response = agent.chat(query)
        return str(response)
    except Exception as e:
        print(f"Error getting agent response: {e}")
        return None

def format_response_for_voice(response: str) -> str:
    """
    Format the response to be more suitable for voice output
    """
    # Add periods for better speech pacing
    response = response.replace("\n", ". ")
    
    # Remove any special characters that might interfere with speech
    response = response.replace("*", "")
    response = response.replace("#", "number")
    
    return response

@app.route("/voice", methods=['POST'])
def handle_voice():
    """
    Handle incoming voice calls
    """
    # Create TwiML response object
    twiml = VoiceResponse()
    
    # Get spoken input from the call
    spoken_text = request.values.get('SpeechResult', '')
    
    if not spoken_text:
        # If no speech detected, ask for input
        gather = twiml.gather(
            input='speech',
            action='/process_speech',
            method='POST',
            language='en-US',
            speechTimeout='auto'
        )
        gather.say("Please ask your question about Rapamycin.")
    else:
        # Process the speech immediately
        agent_response = get_agent_response(spoken_text)
        
        if agent_response:
            # Format response for voice
            voice_response = format_response_for_voice(agent_response)
            
            # Read the response
            twiml.say(voice_response, voice='alice')
        else:
            twiml.say("I apologize, but I encountered an error processing your request.")
    
    return str(twiml)

@app.route("/process_speech", methods=['POST'])
def process_speech():
    """
    Process spoken input and generate response
    """
    # Create TwiML response object
    twiml = VoiceResponse()
    
    # Get the spoken text
    spoken_text = request.values.get('SpeechResult', '')
    
    if spoken_text:
        # Get response from agent
        agent_response = get_agent_response(spoken_text)
        
        if agent_response:
            # Format response for voice
            voice_response = format_response_for_voice(agent_response)
            
            # Read the response
            twiml.say(voice_response, voice='alice')
        else:
            twiml.say("I apologize, but I encountered an error processing your request.")
    else:
        twiml.say("I didn't catch that. Could you please repeat your question?")
    
    return str(twiml)

if __name__ == "__main__":
    # Make sure to use SSL when deploying to production
    app.run(debug=True, port=5000)