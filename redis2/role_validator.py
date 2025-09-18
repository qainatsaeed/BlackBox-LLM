"""
Role validator module for HRAsk system - validates user roles and creates filters
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class User:
    """User data class for role validation"""
    user_id: str
    role: str
    account_id: Optional[str] = None
    accessible_locations: Optional[List[str]] = None
    team_employees: Optional[List[str]] = None

class RoleValidator:
    def __init__(self):
        """Initialize role validator with default role permissions"""
        # Define role hierarchy (higher number = more permissions)
        self.role_levels = {
            "employee": 1,
            "supervisor": 2,
            "manager": 3,
            "admin": 4
        }
    
    def validate_role(self, query_data: Dict[str, Any]) -> User:
        """
        Validate user role from query data and return User object
        """
        user_id = query_data.get('user_id', '')
        role = query_data.get('user_role', 'employee').lower()
        account_id = query_data.get('account_id', '')
        location_ids = query_data.get('location_ids', [])
        
        # Convert to list if single string
        if isinstance(location_ids, str):
            location_ids = [location_ids]
        
        # Default to valid role
        if role not in self.role_levels:
            logger.warning(f"Invalid role '{role}' for user '{user_id}', defaulting to 'employee'")
            role = 'employee'
        
        # Get team members (in real app, would query a database)
        team_members = self._get_team_members(user_id, role)
        
        return User(
            user_id=user_id,
            role=role,
            account_id=account_id,
            accessible_locations=location_ids,
            team_employees=team_members
        )
    
    def _get_team_members(self, user_id: str, role: str) -> List[str]:
        """
        Get team members for a given user (mock implementation)
        In real app, this would query a database
        """
        # Mock team mappings - in real implementation, would query DB
        if role == 'supervisor':
            # Mock supervisor -> employees mapping
            return ["emp001", "emp002", "emp003"]
        elif role == 'manager':
            # Mock manager -> all location employees mapping
            return ["emp001", "emp002", "emp003", "emp004", "emp005"]
        elif role == 'admin':
            # Admins see everything
            return []
        else:
            # Employees only see themselves
            return [user_id]
    
    def create_filters(self, user: User) -> Dict[str, Any]:
        """
        Create filters for document retrieval based on user role
        """
        filters = {}
        
        # Apply account isolation
        if user.account_id:
            filters["account_id"] = user.account_id
        
        # Location-based filtering
        if user.accessible_locations:
            filters["location_id"] = {"$in": user.accessible_locations}
        
        # Employee-based filtering
        if user.role != 'admin' and user.team_employees:
            filters["employee_id"] = {"$in": user.team_employees}
        
        return filters
    
    def apply_document_filters(self, docs: List[Any], user: User) -> List[Any]:
        """
        Filter documents based on user role and permissions
        """
        if user.role == 'admin':
            return docs  # Admins see everything
        
        filtered_docs = []
        for doc in docs:
            meta = getattr(doc, 'meta', {})
            
            # Employee filtering - employees only see their own data
            if user.role == 'employee' and user.user_id:
                if meta.get('employee', '').lower() == user.user_id.lower():
                    filtered_docs.append(doc)
                # Or general sales/public data
                elif meta.get('data_type') in ['sales_breakdown', 'public']:
                    filtered_docs.append(doc)
            
            # Supervisor filtering - supervisors see team data
            elif user.role == 'supervisor' and user.team_employees:
                if (meta.get('employee', '').lower() in [e.lower() for e in user.team_employees] or
                    meta.get('data_type') in ['sales_breakdown', 'public']):
                    filtered_docs.append(doc)
            
            # Manager filtering - managers see location data
            elif user.role == 'manager' and user.accessible_locations:
                location = meta.get('location', '')
                if (not location or 
                    location.lower() in [loc.lower() for loc in user.accessible_locations] or
                    meta.get('data_type') in ['sales_breakdown', 'public']):
                    filtered_docs.append(doc)
            
        return filtered_docs