"""
Simplified training script for BioBlood ML models
This script will train the models and save them for Azure deployment
"""
import os
import sys

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'numpy', 'sklearn', 'tensorflow', 'joblib', 'PIL', 'cv2'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            elif package == 'cv2':
                import cv2
            elif package == 'sklearn':
                import sklearn
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        print("\nPlease install them using:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def create_sample_dataset():
    """Create a small sample dataset for testing if no dataset exists"""
    import numpy as np
    from PIL import Image
    
    print("Creating sample dataset for testing...")
    
    # Create dataset directory structure
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    
    for group in blood_groups:
        os.makedirs(f'dataset/{group}', exist_ok=True)
        
        # Create 10 sample images per blood group (96x96 grayscale)
        for i in range(10):
            # Generate random fingerprint-like pattern
            img_array = np.random.randint(0, 256, (96, 96), dtype=np.uint8)
            
            # Add some structure to make it more fingerprint-like
            for _ in range(5):
                x, y = np.random.randint(10, 86, 2)
                cv2.circle(img_array, (x, y), np.random.randint(5, 15), 
                          np.random.randint(100, 200), -1)
            
            # Save image
            img = Image.fromarray(img_array, 'L')
            img.save(f'dataset/{group}/sample_{i}.png')
    
    print("Sample dataset created!")

def main():
    print("=== BioBlood Model Training ===")
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Check if dataset exists
    if not os.path.exists('dataset'):
        print("No dataset folder found.")
        print("Options:")
        print("1. Download from Azure Blob Storage using download_dataset.py")
        print("2. Create sample dataset for testing")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == '1':
            print("Please run download_dataset.py first to get your dataset from Azure Blob Storage")
            return
        elif choice == '2':
            import cv2  # Import here to avoid error if not installed
            create_sample_dataset()
        else:
            print("Invalid choice. Exiting.")
            return
    
    # Import and run the training script
    print("Starting model training...")
    try:
        # Import the training script
        import train_ensemble
        print("Training completed successfully!")
        print("Models saved in 'saved_models/' directory")
        
    except Exception as e:
        print(f"Training failed: {e}")
        print("Please check the error and try again.")

if __name__ == "__main__":
    main()
