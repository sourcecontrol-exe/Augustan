#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Project Board Sync Script

Automatically syncs TODO.md with GitHub Project Board
"""

import os
import re
import json
import requests
from datetime import datetime

class GitHubKanbanSync:
    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        self.repo_owner = os.environ.get('REPO_OWNER')
        self.repo_name = os.environ.get('REPO_NAME')
        self.project_id = os.environ.get('PROJECT_ID', '3')  # Default to project 3
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
    def parse_todo_file(self):
        """Parse TODO.md and extract tasks"""
        if not os.path.exists('TODO.md'):
            print("❌ TODO.md not found")
            return []
            
        with open('TODO.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        tasks = []
        current_milestone = None
        
        lines = content.split('\n')
        for line in lines:
            # Milestone detection
            if line.startswith('## Milestone'):
                current_milestone = line.replace('## ', '').split(':')[0]
                
            # Task detection
            elif line.startswith('### ['):
                is_completed = '[x]' in line.lower() or '[✓]' in line
                task_name = re.sub(r'### \[.\] ', '', line)
                
                # Extract task details
                task_details = []
                
                tasks.append({
                    'title': task_name,
                    'milestone': current_milestone,
                    'completed': is_completed,
                    'details': task_details,
                    'labels': [current_milestone.replace(' ', '-').lower()] if current_milestone else []
                })
        
        return tasks
    
    def get_existing_project(self):
        """Get existing GitHub Project Board by ID"""
        # Use the specific project ID from environment or default
        return self.project_id
    
    def setup_project_columns(self, project_id):
        """Setup project columns"""
        columns = ['To Do', 'In Progress', 'Done']
        
        for column_name in columns:
            url = f"https://api.github.com/projects/{project_id}/columns"
            column_data = {'name': column_name}
            requests.post(url, headers=self.headers, json=column_data)
    
    def get_project_columns(self, project_id):
        """Get project columns"""
        url = f"https://api.github.com/projects/{project_id}/columns"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            columns = response.json()
            return {col['name']: col['id'] for col in columns}
        
        return {}
    
    def create_or_update_issues(self, tasks):
        """Create or update GitHub issues for tasks"""
        # Get existing issues
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues"
        response = requests.get(url, headers=self.headers)
        existing_issues = {issue['title']: issue for issue in response.json()} if response.status_code == 200 else {}
        
        created_issues = []
        
        for task in tasks:
            if task['title'] in existing_issues:
                # Update existing issue
                issue = existing_issues[task['title']]
                if task['completed'] and issue['state'] == 'open':
                    # Close completed task
                    close_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues/{issue['number']}"
                    requests.patch(close_url, headers=self.headers, json={'state': 'closed'})
                    
                created_issues.append(issue)
            else:
                # Create new issue
                issue_data = {
                    'title': task['title'],
                    'body': f"**Milestone**: {task['milestone']}\n\nAutomatically created from TODO.md",
                    'labels': task['labels'],
                    'state': 'closed' if task['completed'] else 'open'
                }
                
                response = requests.post(url, headers=self.headers, json=issue_data)
                if response.status_code == 201:
                    created_issues.append(response.json())
        
        return created_issues
    
    def sync_project_board(self):
        """Main sync function"""
        print("🔄 Starting Kanban board sync...")
        
        # Parse TODO.md
        tasks = self.parse_todo_file()
        if not tasks:
            print("❌ No tasks found in TODO.md")
            return False
        
        print(f"📋 Found {len(tasks)} tasks in TODO.md")
        
        # Get existing project
        project_id = self.get_existing_project()
        if not project_id:
            print("❌ Failed to get project board ID")
            return False
        
        print(f"🎯 Using existing project board ID: {project_id}")
        
        # Create/update issues
        issues = self.create_or_update_issues(tasks)
        print(f"✅ Processed {len(issues)} issues")
        
        # Get project columns
        columns = self.get_project_columns(project_id)
        
        # Add issues to appropriate columns
        for i, task in enumerate(tasks):
            if i < len(issues):
                issue = issues[i]
                column_name = 'Done' if task['completed'] else 'To Do'
                
                if column_name in columns:
                    # Check if card already exists
                    existing_cards_url = f"https://api.github.com/projects/columns/{columns[column_name]}/cards"
                    existing_cards = requests.get(existing_cards_url, headers=self.headers)
                    
                    card_exists = False
                    if existing_cards.status_code == 200:
                        for card in existing_cards.json():
                            if card.get('content_url') and str(issue['id']) in card['content_url']:
                                card_exists = True
                                break
                    
                    if not card_exists:
                        # Add card to column
                        card_data = {
                            'content_id': issue['id'],
                            'content_type': 'Issue'
                        }
                        requests.post(existing_cards_url, headers=self.headers, json=card_data)
        
        print("✅ Kanban board sync completed!")
        return True

def main():
    """Main entry point"""
    syncer = GitHubKanbanSync()
    
    if not all([syncer.token, syncer.repo_owner, syncer.repo_name]):
        print("❌ Missing required environment variables")
        print("   Required: GITHUB_TOKEN, REPO_OWNER, REPO_NAME")
        return False
    
    return syncer.sync_project_board()

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
