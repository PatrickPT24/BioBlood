# Download Models from Microsoft Fabric

## 📥 **Step-by-Step Guide to Download Your Trained Models**

### **Step 1: Access Your Fabric Workspace**
1. Go to [Microsoft Fabric](https://app.fabric.microsoft.com/)
2. Login with your Azure student account
3. Navigate to your workspace where you trained the models

### **Step 2: Download Model Files**
You need to download these 5 files from your Fabric workspace:

#### **Required Model Files:**
1. **`enhanced_ensemble_blood_group_model.pkl`** - Your main ensemble model
2. **`cnn_blood_group_model.h5`** - CNN model
3. **`svm_complete_pipeline.pkl`** - SVM model with preprocessing
4. **`rf_blood_group_model.pkl`** - Random Forest model
5. **`label_encoder.pkl`** - Label encoder for blood groups

### **Step 3: Locate Files in Fabric**
The files should be in one of these locations:
- **Files section** of your workspace
- **Lakehouse** → **Files** folder
- **Notebook outputs** from your training notebooks

### **Step 4: Download Process**
1. **Navigate to Files section** in your Fabric workspace
2. **Find each model file** listed above
3. **Right-click** on each file
4. **Select "Download"**
5. **Save to your computer** in a folder called `models`

### **Step 5: Organize Downloaded Files**
Create this folder structure on your computer:
```
your_project/
├── models/
│   ├── enhanced_ensemble_blood_group_model.pkl
│   ├── cnn_blood_group_model.h5
│   ├── svm_complete_pipeline.pkl
│   ├── rf_blood_group_model.pkl
│   └── label_encoder.pkl
├── backend/
│   ├── app.py
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── styles.css
    └── script.js
```

### **Step 6: Verify Downloads**
Check that all files are downloaded and have reasonable sizes:
- **enhanced_ensemble_blood_group_model.pkl**: Should be largest (contains all models)
- **cnn_blood_group_model.h5**: TensorFlow model file
- **svm_complete_pipeline.pkl**: Scikit-learn pipeline
- **rf_blood_group_model.pkl**: Random Forest model
- **label_encoder.pkl**: Small file with blood group labels

### **Alternative: If Files Not Found**
If you can't find the model files:

1. **Re-run the last cell** of each training notebook to save models again
2. **Check the notebook outputs** for file paths
3. **Look in different workspace sections**:
   - Data Engineering → Lakehouse → Files
   - Data Science → Models
   - Workspace → Browse → Files

### **Step 7: Upload to Azure (After Download)**
Once you have all model files:
1. **Copy them to the `models` folder** in your project
2. **Run the deployment script** to upload everything to Azure
3. **Your app will automatically load** these models

## 🚨 **Important Notes:**
- **All 5 files are required** for the app to work properly
- **File names must match exactly** as shown above
- **Keep files in the `models` folder** for the backend to find them
- **Enhanced ensemble model is the primary model** - others are backups

## 🔧 **Troubleshooting:**
- **File not found**: Check different sections of your Fabric workspace
- **Download fails**: Try downloading one file at a time
- **Large file size**: Enhanced ensemble might be 100MB+ (normal)
- **Permission issues**: Make sure you have access to the workspace

## ✅ **Verification:**
After downloading, you should have:
- ✅ 5 model files in `models` folder
- ✅ Total size around 100-500MB
- ✅ All files have `.pkl` or `.h5` extensions
- ✅ Files are not corrupted (can be opened)

**Once you have all files, proceed with the Azure deployment!** 🚀
