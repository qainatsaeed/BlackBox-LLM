"""
Model manager module for HRAsk system - multi-LLM flexibility
"""
import os
import yaml
import logging
import requests
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, config_path: str = "models.yml"):
        """
        Initialize ModelManager with configuration from models.yml
        """
        self.config_path = config_path
        self.models = {}
        self.default_model = None
        self.load_config()
        
    def load_config(self) -> None:
        """
        Load model configuration from YAML file
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as file:
                    config = yaml.safe_load(file)
                    self.models = config.get('models', {})
                    self.default_model = config.get('default_model')
                    
                    if not self.default_model and self.models:
                        self.default_model = next(iter(self.models))
                        
                logger.info(f"Loaded {len(self.models)} models from config")
            else:
                # Default configuration if file doesn't exist
                self.models = {
                    "llama3.1:8b": {
                        "provider": "ollama",
                        "endpoint": "http://ollama:11434/api/generate",
                        "context_length": 8192,
                        "prompt_template": "You're an HR assistant answering questions based on employee data. Only use the provided context.\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:",
                        "parameters": {
                            "temperature": 0.1,
                            "num_predict": 150
                        }
                    }
                }
                self.default_model = "llama3.1:8b"
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                
                # Write default config
                self.save_config()
        except Exception as e:
            logger.error(f"Error loading model config: {str(e)}")
            
            # Fallback to defaults
            self.models = {
                "llama3.1:8b": {
                    "provider": "ollama",
                    "endpoint": "http://ollama:11434/api/generate",
                    "prompt_template": "You're an HR assistant answering questions based on employee data. Only use the provided context.\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:",
                    "parameters": {
                        "temperature": 0.1,
                        "num_predict": 150
                    }
                }
            }
            self.default_model = "llama3.1:8b"
    
    def save_config(self) -> None:
        """
        Save model configuration to YAML file
        """
        try:
            config = {
                'models': self.models,
                'default_model': self.default_model
            }
            
            with open(self.config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False)
                
            logger.info(f"Saved model config to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving model config: {str(e)}")
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available model names
        """
        return list(self.models.keys())
    
    async def query_model(self, model_name: str, query: str, context: str, 
                         user_role: str = None) -> str:
        """
        Query specified model with prompt
        """
        # Use specified model or default
        model_name = model_name if model_name in self.models else self.default_model
        model_config = self.models[model_name]
        
        # Get provider
        provider = model_config.get('provider', 'ollama').lower()
        
        # Format prompt using template
        template = model_config.get('prompt_template', "{context}\n\nQuestion: {query}\n\nAnswer:")
        role_prefix = self._get_role_prefix(user_role) if user_role else ""
        prompt = template.format(context=context, query=query, role=role_prefix)
        
        # Call appropriate provider method
        if provider == 'ollama':
            return await self._query_ollama(model_name, prompt, model_config)
        elif provider == 'openai':
            return await self._query_openai(model_name, prompt, model_config)
        else:
            logger.error(f"Unsupported model provider: {provider}")
            return f"Error: Unsupported model provider {provider}"
    
    async def _query_ollama(self, model_name: str, prompt: str, 
                           config: Dict[str, Any]) -> str:
        """
        Query Ollama API with prompt
        """
        try:
            # Extract model name without provider prefix
            model_id = model_name.split(':')[0] if ':' in model_name else model_name
            
            # Create payload
            payload = {
                "model": model_id,
                "prompt": prompt,
                "stream": False,
                "options": config.get('parameters', {})
            }
            
            # Get endpoint from config or use default
            endpoint = config.get('endpoint', "http://ollama:11434/api/generate")
            
            # Make request
            response = requests.post(endpoint, json=payload, timeout=100)
            response.raise_for_status()
            result = response.json()
            
            return result.get("response", "No response generated")
        except Exception as e:
            logger.error(f"Error querying Ollama: {str(e)}")
            return f"Error querying model: {str(e)}"
    
    async def _query_openai(self, model_name: str, prompt: str, 
                           config: Dict[str, Any]) -> str:
        """
        Query OpenAI API with prompt
        """
        try:
            # Implement OpenAI API call
            # For Milestone 2, we'll return an error as this is not implemented yet
            return "OpenAI API integration not implemented in this milestone"
        except Exception as e:
            logger.error(f"Error querying OpenAI: {str(e)}")
            return f"Error querying OpenAI model: {str(e)}"
    
    def _get_role_prefix(self, user_role: str) -> str:
        """
        Get role-specific prefix for prompts
        """
        role_prefixes = {
            "employee": "You're answering for an employee. Only provide information relevant to this specific employee.",
            "supervisor": "You're answering for a supervisor. Provide team-level information for their supervised employees.",
            "manager": "You're answering for a manager. Provide location-level performance and team data.",
            "admin": "You're answering for an administrator. Provide comprehensive information as requested."
        }
        return role_prefixes.get(user_role, "")