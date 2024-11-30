from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import time
from twilio.rest import Client
from dotenv import load_dotenv
from urllib.parse import parse_qs
import requests

load_dotenv()

# Twilio client initialization
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
model_url = os.environ.get('MODEL_URL')
client_twilio = Client(account_sid, auth_token)

# Twilio WhatsApp sandbox number
twilio_whatsapp_number = 'whatsapp:+14155238886'

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        if self.path == '/whatsapp':
            post_data = parse_qs(post_data.decode('utf-8'))
            print(post_data)

            incoming_msg = post_data.get('Body', [''])[0]
            sender_name = post_data.get('ProfileName', [''])[0]
            sender_number = post_data.get('From', [''])[0].replace('whatsapp:', '')

            # Event details or knowledge base document (example) - NOT sent to Twilio
            event_details = {
                "Event Name": "Intercollege Coding Challenge 2024",
                "Date": "12th December 2024",
                "Location": "XYZ University, Auditorium Hall",
                "Duration": "10 AM to 6 PM",
                "Competition Format": "Team-based coding rounds, algorithm challenges, and problem-solving contests",
                "Prizes": "1st place - $1000, 2nd place - $500, 3rd place - $250",
                "Event Highlights": "Live coding sessions, keynote by industry experts, networking opportunities, workshops on data structures and algorithms, and tech talks by top-tier companies.",
                "Eligibility": "Open to college students from all fields of study",
                "Contact Info": "coding@xyzuniversity.edu"
            }

            # Create the input for the model: only send the incoming message to the model for context
            model_input = f"User: {incoming_msg} \n\nEvent Info: {event_details}"

            # Get response from LM Studio's API
            response = self.process_user_message(model_input)

            if response is None:
                response = "Failed to process incoming message."

            print("\n\n\n\n!!!!!RESPONSE:" + response)
            # Send the model response back to WhatsApp (only the response)
            self.send_whatsapp_message(sender_number, response)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_data = json.dumps({'response': response})
            self.wfile.write(response_data.encode('utf-8'))

        else:
            self.send_error(404)

    # Function to send a WhatsApp message
    def send_whatsapp_message(self, recipient_number, message_body):
        print("RECIPIENT NUMBER:" + str(recipient_number))
        # Check if message exceeds Twilio's limit (1600 chars)
        message = client_twilio.messages.create(
            body=message_body,
            from_=twilio_whatsapp_number,
            to=f'whatsapp:{recipient_number}'
        )
        print(f"Sent WhatsApp message to {recipient_number}: {message_body}")

    def process_user_message(self, user_message):
        # Send the user message and event context to LM Studio API
        headers = {
            "Content-Type": "application/json",  # Required for LM Studio's API
        }

        # Payload for LM Studio's chat completions endpoint
        payload = {
            "model": "llama-2-7b",  # The model you are using (adjust as needed)
            "messages": [{"role": "user", "content": user_message}],  # User message context
        }

        # Use the LM Studio's API to get a response from the model
        response = requests.post(
            model_url,  # LM Studio's local endpoint
            headers=headers,
            json=payload
        )

        # Check the response status
        if response.status_code == 200:
            result = response.json()

            # Print the result for debugging purposes
            print("LM Studio Response:", result)

            # Assuming response is in the format: {"choices": [{"message": {"content": "response text"}}]}
            if isinstance(result, dict) and 'choices' in result and len(result['choices']) > 0:
                generated_text = result['choices'][0].get('message', {}).get('content')
                if generated_text:
                    return generated_text
                else:
                    print("No generated text found")
                    return "Sorry, I couldn't generate a response."

        else:
            # If there's an error with the API call, print the status and message
            print(f"Error with LM Studio API: {response.status_code} - {response.text}")
            return "Error with LM Studio API."

class MyHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)

def run_server():
    port = 22222
    server_address = ('', port)
    httpd = MyHTTPServer(server_address, MyHTTPRequestHandler)
    print(f"Server running on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()