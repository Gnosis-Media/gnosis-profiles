import requests
import logging
from pprint import pprint
from datetime import datetime
from secrets_manager import get_service_secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration
PROFILE_SERVICE_URL = 'http://44.204.146.40:80'
secrets = get_service_secrets('gnosis-profiles')
API_KEY = secrets.get('API_KEY')

def test_user_profile():
    """Test user profile creation and retrieval"""
    
    # Test user data
    test_user = {
        'user_id': 999,  # Test user ID
        'display_name': 'Test User',
        'name': 'Test User Full Name',
        'bio': 'This is a test user profile for the Gnosis platform',
        'location': 'Test Location',
        'profile_pic_url': 'https://example.com/test.jpg'
    }
    
    logging.info("\nTesting User Profile Creation:")
    try:
        # Create user profile
        response = requests.post(
            f"{PROFILE_SERVICE_URL}/api/users",
            json=test_user,
            headers={'X-API-KEY': API_KEY}
        )
        logging.info(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 201:
            logging.info("User profile created successfully")
            logging.info(f"Response: {response.json()}")
        else:            
            logging.error(f"Failed to create user profile: {response.json()}")
            
        # Get user profile
        response = requests.get(
            f"{PROFILE_SERVICE_URL}/api/users/{test_user['user_id']}", 
            headers={'X-API-KEY': API_KEY}
        )
        
        if response.status_code == 200 or response.status_code == 201:
            logging.info("\nRetrieved User Profile:")
            pprint(response.json())
        else:
            logging.error(f"Failed to retrieve user profile: {response.json()}")
            
    except Exception as e:
        logging.error(f"Error in user profile test: {str(e)}")

def test_ai_profile_creation():
    """Test AI profile creation and retrieval for specific content"""
    
    # Test with content IDs 29 and 30
    content_ids = [12, 13]
    
    for content_id in content_ids:
        logging.info(f"\nTesting AI Profile Creation for Content ID {content_id}:")
        try:
            # Create AI profile
            response = requests.post(
                f"{PROFILE_SERVICE_URL}/api/ais",
                json={'content_id': content_id},
                headers={'X-API-KEY': API_KEY}
            )
            
            if response.status_code == 201 or response.status_code == 200:
                logging.info(f"AI profile created successfully for content {content_id}")
                logging.info(f"Response: {response.json()}")
                
                # Get AI profile
                response = requests.get(
                    f"{PROFILE_SERVICE_URL}/api/ais/content/{content_id}",
                    headers={'X-API-KEY': API_KEY}
                )
                logging.info(f"Response Status Code: {response.status_code}")
                if response.status_code == 200 or response.status_code == 201:
                    logging.info(f"\nRetrieved AI Profile for content {content_id}:")
                    pprint(response.json())
                else:
                    logging.error(f"Failed to retrieve AI profile: {response.json()}")
            else:
                logging.error(f"Failed to create AI profile: {response.json()}")
                
        except Exception as e:
            logging.error(f"Error in AI profile test for content {content_id}: {str(e)}")

def test_ai_profile_retrieval():
    """Test retrieving existing AI profiles"""
    
    content_ids = [29, 30]
    
    logging.info("\nTesting AI Profile Retrieval for existing profiles:")
    
    for content_id in content_ids:
        try:
            response = requests.get(
                f"{PROFILE_SERVICE_URL}/api/ais/content/{content_id}",
                headers={'X-API-KEY': API_KEY}
            )
            logging.info(f"Response Status Code: {response.status_code}")
            if response.status_code == 200 or response.status_code == 201:
                logging.info(f"\nRetrieved AI Profile for content {content_id}:")
                profile = response.json()
                logging.info(f"Display Name: {profile.get('display_name')}")
                logging.info(f"Bio: {profile.get('bio')}")
                logging.info("\nSystem Instructions:")
                logging.info(profile.get('systems_instructions'))
            else:
                logging.error(f"No profile found for content {content_id}")
                
        except Exception as e:
            logging.error(f"Error retrieving AI profile for content {content_id}: {str(e)}")

def run_tests():
    """Run all tests"""
    logging.info("Starting profile service tests...")
    
    logging.info("\n=== Testing User Profile Functionality ===")
    test_user_profile()
    
    logging.info("\n=== Testing AI Profile Creation ===")
    test_ai_profile_creation()
    
    logging.info("\n=== Testing AI Profile Retrieval ===")
    test_ai_profile_retrieval()
    
    logging.info("\nTests completed!")

if __name__ == "__main__":
    run_tests()