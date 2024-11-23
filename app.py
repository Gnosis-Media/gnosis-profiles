from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
from datetime import datetime
from openai import OpenAI
import logging
import json
import os
from secrets_manager import get_service_secrets

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__)
CORS(app)

secrets = get_service_secrets('gnosis-profiles')

C_PORT = int(secrets.get('PORT', 5000))
SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{secrets['MYSQL_USER']}:{secrets['MYSQL_PASSWORD_PROFILES']}"
    f"@{secrets['MYSQL_HOST']}:{secrets['MYSQL_PORT']}/{secrets['MYSQL_DATABASE']}"
)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

QUERY_API_URL = secrets.get('QUERY_API_URL')

OPENAI_API_KEY = secrets.get('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

db = SQLAlchemy(app)

# Models
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(255))
    name = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text)
    location = db.Column(db.String(255))
    profile_pic_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AI(db.Model):
    __tablename__ = 'ais'
    ai_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_id = db.Column(db.Integer, nullable=False)
    display_name = db.Column(db.String(255))
    name = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text)
    profile_pic_url = db.Column(db.String(512))
    location = db.Column(db.String(255))
    systems_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def generate_ai_profile(content):    
    """Generate AI profile using GPT"""
    prompt = f"""
Based on the following content information, create a detailed social media profile for an AI agent that embodies the author's persona in the context of their work.

Content Details:
Title: {content.get('title')}
Author: {content.get('author')}
Topic: {content.get('topic')}
Genre: {content.get('genre')}

Take into account the following custom prompt:
Custom Prompt: {content.get('custom_prompt')}

Make all of the below clever, witty, and engaging.

First describe the following:
Who is the author?
What are they writing about?
Describe their tone and writing style.
What is their persona? their character? their values? their worldview?

Then create a profile that includes:
1. A witty display name that reflects the author's persona
2. A full name (if known)
3. A a social media bio written in the style of the author (be witty and original)
4. A location related to the author or their work (make it something unique/funny)
5. Detailed system instructions for how this AI should communicate. Describe the tone, style, and personality of the author. Take on the persona of the author and describe to the AI how it should act. E.g. "You are Julius Caesar in his writing of De Bello Gallico, your verbiage is precise and to the point, and you are detailed in your descriptions of military strategy. etc etc"

Please respond in JSON format with the following structure:
{{
    "display_name": "Creative display name",
    "name": "Full name",
    "bio": "Detailed biography",
    "location": "Relevant location",
    "systems_instructions": "Detailed instructions for AI communication style"
}}
"""
    logging.info(f"Generating AI profile for content: {content.get('title')}")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a profile creation specialist."},
                {"role": "user", "content": prompt}
            ]
        )

        logging.debug(f"OpenAI response: {response.choices[0].message.content}")
        
        response_text = response.choices[0].message.content
        response_text = response_text.replace("```json", "").replace("```", "")
        profile_data = json.loads(response_text)
        return profile_data
        
    except Exception as e:
        logging.error(f"Error generating AI profile: {str(e)}")
        return None

@app.route('/api/users', methods=['POST'])
def create_or_update_user():
    """Create or update a user profile"""
    try:
        data = request.json
        user_id = data['user_id']

        if user_id is None:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Check if user exists
        user = User.query.get(user_id)
        is_update = user is not None
        
        if not user:
            # Create new user
            user = User(user_id=user_id)
        
        # Update user fields
        user.display_name = data.get('display_name', user.display_name if is_update else None)
        user.name = data.get('name', user.name if is_update else None)
        user.bio = data.get('bio', user.bio if is_update else None)
        user.location = data.get('location', user.location if is_update else None)
        user.profile_pic_url = data.get('profile_pic_url', user.profile_pic_url if is_update else None)
        
        if not is_update:
            db.session.add(user)
        
        db.session.commit()
        
        return jsonify({
            'message': f'User profile {"updated" if is_update else "created"} successfully',
            'user_id': user.user_id,
            'action': 'updated' if is_update else 'created'
        }), 200 if is_update else 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating/updating user profile: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/ais', methods=['POST'])
def create_or_update_ai():
    """Create or update an AI profile based on content"""
    try:
        data = request.json
        content_id = data['content_id']

        if content_id is None:
            return jsonify({'error': 'Content ID is required'}), 400
        
        # Check if AI profile exists for this content
        ai = AI.query.filter_by(content_id=content_id).first()
        is_update = ai is not None
        
        # Get content information by querying gnosis-query
        content_response = requests.get(f'{QUERY_API_URL}/api/content/{content_id}')
        if content_response.status_code != 200:
            return jsonify({'error': 'Content not found'}), 404
        
        content = content_response.json()
            
        # Generate AI profile
        profile_data = generate_ai_profile(content)
        if not profile_data:
            return jsonify({'error': 'Failed to generate AI profile'}), 500
            
        if not ai:
            # Create new AI profile
            ai = AI(content_id=content_id)
        
        # Update AI fields
        ai.display_name = profile_data.get('display_name', ai.display_name if is_update else None)
        ai.name = profile_data.get('name', ai.name if is_update else None)
        ai.bio = profile_data.get('bio', ai.bio if is_update else None)
        ai.location = profile_data.get('location', ai.location if is_update else None)
        ai.systems_instructions = profile_data.get('systems_instructions', ai.systems_instructions if is_update else None)
        ai.profile_pic_url = data.get('profile_pic_url', ai.profile_pic_url if is_update else None)
        
        if not is_update:
            db.session.add(ai)
        
        db.session.commit()
        
        return jsonify({
            'message': f'AI profile {"updated" if is_update else "created"} successfully',
            'ai_id': ai.ai_id,
            'content_id': ai.content_id,
            'action': 'updated' if is_update else 'created'
        }), 200 if is_update else 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating/updating AI profile: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user profile by user_id"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'user_id': user.user_id,
            'display_name': user.display_name,
            'name': user.name,
            'bio': user.bio,
            'location': user.location,
            'profile_pic_url': user.profile_pic_url,
            'created_at': user.created_at.isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting user profile: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/ais/content/<int:content_id>', methods=['GET'])
def get_ai_by_content(content_id):
    """Get AI profile by content_id"""
    try:
        ai = AI.query.filter_by(content_id=content_id).first()
        if not ai:
            return jsonify({'error': 'AI profile not found'}), 404
            
        return jsonify({
            'ai_id': ai.ai_id,
            'content_id': ai.content_id,
            'display_name': ai.display_name,
            'name': ai.name,
            'bio': ai.bio,
            'location': ai.location,
            'profile_pic_url': ai.profile_pic_url,
            'systems_instructions': ai.systems_instructions,
            'created_at': ai.created_at.isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting AI profile: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=C_PORT)