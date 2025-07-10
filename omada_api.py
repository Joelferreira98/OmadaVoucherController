import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app import db
from models import OmadaConfig
import os

class OmadaAPI:
    def __init__(self):
        self.base_url = os.environ.get("OMADA_CONTROLLER_URL", "https://omada.camstm.com:8043")
        self.client_id = os.environ.get("OMADA_CLIENT_ID")
        self.client_secret = os.environ.get("OMADA_CLIENT_SECRET")
        self.omadac_id = os.environ.get("OMADA_OMADAC_ID")
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.session = requests.Session()
        self.session.verify = False  # For development, should be True in production
        
    def _get_config(self) -> Optional[OmadaConfig]:
        """Get Omada configuration from database"""
        return OmadaConfig.query.filter_by(is_active=True).first()
    
    def _save_config(self, config_data: Dict):
        """Save Omada configuration to database"""
        config = self._get_config()
        if not config:
            config = OmadaConfig(
                controller_url=self.base_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                omadac_id=self.omadac_id
            )
            db.session.add(config)
        
        config.access_token = config_data.get('access_token')
        config.refresh_token = config_data.get('refresh_token')
        if config_data.get('expires_in'):
            config.token_expires_at = datetime.utcnow() + timedelta(seconds=config_data['expires_in'])
        config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update instance variables
        self.access_token = config.access_token
        self.refresh_token = config.refresh_token
        self.token_expires_at = config.token_expires_at
    
    def _load_tokens(self):
        """Load tokens from database"""
        config = self._get_config()
        if config:
            self.access_token = config.access_token
            self.refresh_token = config.refresh_token
            self.token_expires_at = config.token_expires_at
            self.base_url = config.controller_url
            self.client_id = config.client_id
            self.client_secret = config.client_secret
            self.omadac_id = config.omadac_id
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired"""
        if not self.token_expires_at:
            return True
        return datetime.utcnow() >= self.token_expires_at - timedelta(minutes=5)
    
    def get_access_token(self) -> Optional[str]:
        """Get access token using client credentials"""
        # Load configuration from database
        self._load_tokens()
        
        if not self.client_id or not self.client_secret or not self.omadac_id:
            logging.error("Missing API configuration")
            return None
            
        try:
            url = f"{self.base_url}/openapi/authorize/token?grant_type=client_credentials"
            data = {
                "omadacId": self.omadac_id,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {'Content-Type': 'application/json'}
            
            # Log debug information (without sensitive data)
            logging.info(f"Attempting token request to: {url}")
            logging.info(f"Using omadacId: {self.omadac_id}")
            logging.info(f"Using client_id: {self.client_id}")
            logging.info(f"Client secret configured: {'Yes' if self.client_secret else 'No'}")
            
            response = self.session.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logging.info(f"API Response: {result}")
            
            if result.get('errorCode') == 0:
                token_data = result['result']
                self._save_config({
                    'access_token': token_data['accessToken'],
                    'refresh_token': token_data.get('refreshToken'),
                    'expires_in': token_data.get('expiresIn', 3600)
                })
                logging.info("Token obtained successfully")
                return token_data['accessToken']
            else:
                error_msg = result.get('msg', 'Unknown error')
                logging.error(f"Failed to get access token: {error_msg}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting access token: {str(e)}")
            return None
    
    def refresh_access_token(self) -> Optional[str]:
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            return self.get_access_token()
            
        try:
            url = f"{self.base_url}/openapi/authorize/token"
            params = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = self.session.post(url, params=params, json=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errorCode') == 0:
                token_data = result['result']
                self._save_config({
                    'access_token': token_data['accessToken'],
                    'refresh_token': token_data['refreshToken'],
                    'expires_in': token_data['expiresIn']
                })
                return token_data['accessToken']
            else:
                logging.error(f"Failed to refresh token: {result.get('msg')}")
                return self.get_access_token()
                
        except Exception as e:
            logging.error(f"Error refreshing token: {str(e)}")
            return self.get_access_token()
    
    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token"""
        self._load_tokens()
        
        if not self.access_token or self._is_token_expired():
            if self.refresh_token:
                token = self.refresh_access_token()
            else:
                token = self.get_access_token()
            
            if not token:
                return False
        
        return True
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated request to Omada API"""
        if not self._ensure_valid_token():
            return None
        
        url = f"{self.base_url}/openapi/v1/{self.omadac_id}/{endpoint}"
        headers = {
            'Authorization': f'AccessToken={self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errorCode') == 0:
                return result.get('result')
            else:
                logging.error(f"API Error: {result.get('msg')}")
                return None
                
        except Exception as e:
            logging.error(f"Request error: {str(e)}")
            return None
    
    def get_sites(self, page: int = 1, page_size: int = 100, search_key: str = None, site_type: int = None) -> Optional[List[Dict]]:
        """Get list of sites from Omada Controller"""
        params = {
            "page": page, 
            "pageSize": min(page_size, 1000)  # API limit is 1000
        }
        
        # Add optional parameters
        if search_key:
            params["searchKey"] = search_key
        if site_type is not None:
            params["filters.type"] = str(site_type)
            
        result = self._make_request('GET', 'sites', params=params)
        
        if result:
            logging.info(f"Retrieved {len(result.get('data', []))} sites from page {page}")
            return result.get('data', [])
        return None
    
    def create_voucher_group(self, site_id: str, voucher_data: Dict) -> Optional[Dict]:
        """Create voucher group in Omada Controller"""
        endpoint = f"sites/{site_id}/hotspot/voucher-groups"
        
        logging.info(f"Creating voucher group for site {site_id} with data: {voucher_data}")
        
        # Use the full API response with error handling
        if not self._ensure_valid_token():
            logging.error("Failed to obtain valid token for voucher creation")
            return None
        
        url = f"{self.base_url}/openapi/v1/{self.omadac_id}/{endpoint}"
        headers = {
            'Authorization': f'AccessToken={self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.post(url, headers=headers, json=voucher_data)
            response.raise_for_status()
            
            result = response.json()
            logging.info(f"Voucher group creation response: {result}")
            
            return result
                
        except Exception as e:
            logging.error(f"Error creating voucher group: {str(e)}")
            return None
    
    def get_voucher_summary(self, site_id: str, start_date: str = None, end_date: str = None) -> Optional[Dict]:
        """Get voucher summary from Omada Controller"""
        endpoint = f"sites/{site_id}/hotspot/vouchers/summary"
        params = {}
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
            
        return self._make_request('GET', endpoint, params=params)
    
    def export_vouchers(self, site_id: str, **filters) -> Optional[Dict]:
        """Export vouchers from Omada Controller"""
        endpoint = f"sites/{site_id}/hotspot/vouchers/export"
        return self._make_request('GET', endpoint, params=filters)

# Global instance
omada_api = OmadaAPI()
