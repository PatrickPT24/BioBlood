#!/usr/bin/env python3
"""
Azure Deployment Helper Script
This script helps prepare the application for Azure deployment
"""

import os
import shutil
import zipfile
from pathlib import Path

def create_deployment_package():
    """Create a deployment package for Azure"""
    
    # Files to include in deployment
    files_to_include = [
        'app.py',
        'startup.py',
        'Procfile',
        'gunicorn.conf.py',
        'requirements.txt',
        'runtime.txt',
        'frontend/',
        'models/',
        'uploads/'
    ]
    
    # Create deployment directory
    deploy_dir = 'azure_deployment'
    if os.path.exists(deploy_dir):
        shutil.rmtree(deploy_dir)
    os.makedirs(deploy_dir)
    
    print("📦 Creating Azure deployment package...")
    
    # Copy files
    for item in files_to_include:
        src = Path(item)
        dst = Path(deploy_dir) / item
        
        if src.is_file():
            shutil.copy2(src, dst)
            print(f"✅ Copied file: {item}")
        elif src.is_dir():
            shutil.copytree(src, dst)
            print(f"✅ Copied directory: {item}")
        else:
            print(f"⚠️  File not found: {item}")
    
    # Create zip file
    zip_path = 'azure_deployment.zip'
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, deploy_dir)
                zipf.write(file_path, arc_path)
    
    print(f"✅ Deployment package created: {zip_path}")
    print(f"📁 Deployment directory: {deploy_dir}")
    
    return zip_path, deploy_dir

def verify_deployment_files():
    """Verify that all required files are present"""
    
    required_files = [
        'app.py',
        'startup.py',
        'Procfile',
        'requirements.txt',
        'runtime.txt'
    ]
    
    required_dirs = [
        'frontend',
        'models'
    ]
    
    print("🔍 Verifying deployment files...")
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✅ {file}")
    
    missing_dirs = []
    for dir in required_dirs:
        if not os.path.exists(dir):
            missing_dirs.append(dir)
        else:
            print(f"✅ {dir}/")
    
    if missing_files or missing_dirs:
        print("❌ Missing files/directories:")
        for item in missing_files + missing_dirs:
            print(f"   - {item}")
        return False
    
    print("✅ All required files present!")
    return True

if __name__ == '__main__':
    print("🚀 Azure Deployment Helper")
    print("=" * 50)
    
    # Verify files
    if not verify_deployment_files():
        print("❌ Deployment verification failed!")
        exit(1)
    
    # Create deployment package
    zip_path, deploy_dir = create_deployment_package()
    
    print("\n📋 Deployment Instructions:")
    print("1. Upload the azure_deployment.zip to your Azure App Service")
    print("2. Or use Azure CLI: az webapp deployment source config-zip")
    print("3. Monitor the deployment logs in Azure Portal")
    print("4. Test the webapp at: https://bio-fingerapp-ffgndnaka5afedf6.centralindia-01.azurewebsites.net")
    
    print(f"\n✅ Deployment package ready: {zip_path}")
