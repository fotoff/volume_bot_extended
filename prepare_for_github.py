#!/usr/bin/env python3
"""
Prepare Extended Trading Bot v2 for GitHub publication
This script cleans up development files and prepares a clean repository
"""

import os
import shutil
import glob

# Files to keep for GitHub publication
KEEP_FILES = {
    # Core bot files
    'extended-bot-v2.py',
    'config.py',
    'env.example',
    'requirements.txt',
    
    # Documentation
    'README.md',
    'QUICKSTART.md',
    'DEPLOYMENT.md',
    'API.md',
    'CHANGELOG.md',
    'CONTRIBUTING.md',
    'LICENSE',
    
    # GitHub files
    '.gitignore',
    'prepare_for_github.py',
    
    # Service files
    'extended-bot-rise.service',
}

# Directories to keep
KEEP_DIRS = {
    '.git',
    '__pycache__',  # Will be ignored by .gitignore
}

def clean_repository():
    """Remove development files and keep only production-ready files"""
    current_dir = os.getcwd()
    
    print("🧹 Cleaning repository for GitHub publication...")
    print(f"📁 Working directory: {current_dir}")
    
    # List all files and directories
    all_items = set(os.listdir('.'))
    
    # Files and directories to remove
    to_remove = all_items - KEEP_FILES - KEEP_DIRS
    
    print(f"\n📋 Files to keep ({len(KEEP_FILES)}):")
    for file in sorted(KEEP_FILES):
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (missing)")
    
    print(f"\n🗑️  Files to remove ({len(to_remove)}):")
    for item in sorted(to_remove):
        print(f"  🔸 {item}")
    
    # Confirm before deletion
    response = input(f"\n❓ Remove {len(to_remove)} files/directories? (y/N): ")
    
    if response.lower() == 'y':
        removed_count = 0
        for item in to_remove:
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    print(f"  🗂️  Removed directory: {item}")
                else:
                    os.remove(item)
                    print(f"  📄 Removed file: {item}")
                removed_count += 1
            except Exception as e:
                print(f"  ❌ Error removing {item}: {e}")
        
        print(f"\n✅ Cleanup complete! Removed {removed_count} items.")
        
        # Verify remaining files
        remaining = set(os.listdir('.'))
        print(f"\n📊 Repository contents after cleanup:")
        for item in sorted(remaining):
            if os.path.isdir(item):
                print(f"  📁 {item}/")
            else:
                print(f"  📄 {item}")
                
    else:
        print("❌ Cleanup cancelled.")

def create_github_workflow():
    """Create basic GitHub Actions workflow (optional)"""
    workflow_dir = '.github/workflows'
    os.makedirs(workflow_dir, exist_ok=True)
    
    workflow_content = """name: Extended Trading Bot v2 CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10']

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Validate configuration
      run: |
        python -c "from config import MARKETS; print(f'Markets: {MARKETS}')"
    
    - name: Check code style
      run: |
        # Add linting when available
        echo "Code style check placeholder"
    
    - name: Security check
      run: |
        # Check for hardcoded secrets
        if grep -r "sk-" . --exclude-dir=.git || grep -r "api_key.*=" . --exclude-dir=.git; then
          echo "❌ Potential hardcoded secrets found"
          exit 1
        fi
        echo "✅ No hardcoded secrets detected"
"""
    
    workflow_file = os.path.join(workflow_dir, 'ci.yml')
    with open(workflow_file, 'w') as f:
        f.write(workflow_content)
    
    print(f"📝 Created GitHub workflow: {workflow_file}")

def validate_required_files():
    """Ensure all required files exist and are properly configured"""
    print("\n🔍 Validating required files...")
    
    required_files = [
        'extended-bot-v2.py',
        'config.py', 
        'README.md',
        'LICENSE',
        '.gitignore'
    ]
    
    all_good = True
    for file in required_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"  ✅ {file} ({size} bytes)")
        else:
            print(f"  ❌ {file} (missing)")
            all_good = False
    
    if all_good:
        print("✅ All required files present")
    else:
        print("❌ Some required files are missing")
    
    return all_good

def main():
    print("🚀 Extended Trading Bot v2 - GitHub Preparation Tool")
    print("=" * 60)
    
    # Validate we're in the right directory
    if not os.path.exists('extended-bot-v2.py'):
        print("❌ Error: extended-bot-v2.py not found")
        print("   Please run this script from the bot directory")
        return
    
    # Menu
    while True:
        print("\n📋 Available actions:")
        print("1. 🧹 Clean repository (remove dev files)")
        print("2. 🔍 Validate required files")
        print("3. 📝 Create GitHub workflow (optional)")
        print("4. 📊 Show current repository status")
        print("5. ❌ Exit")
        
        choice = input("\n👉 Select action (1-5): ").strip()
        
        if choice == '1':
            clean_repository()
        elif choice == '2':
            validate_required_files()
        elif choice == '3':
            create_github_workflow()
        elif choice == '4':
            print(f"\n📊 Current repository contents:")
            for item in sorted(os.listdir('.')):
                if os.path.isdir(item):
                    print(f"  📁 {item}/")
                else:
                    size = os.path.getsize(item)
                    print(f"  📄 {item} ({size} bytes)")
        elif choice == '5':
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
