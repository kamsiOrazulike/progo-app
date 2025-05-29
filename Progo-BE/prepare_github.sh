#!/bin/bash

# 🚀 GitHub Preparation Script for Render Deployment
# This script prepares your code for GitHub and Render deployment

echo "🎯 Preparing Progo Backend for GitHub & Render Deployment"
echo "=========================================================="

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Please run this script from the Progo-BE directory"
    exit 1
fi

# Check git status
echo "📋 Checking Git status..."
if [ ! -d ".git" ]; then
    echo "🔧 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository exists"
fi

# Check for required files
echo ""
echo "🔍 Checking required files for Render deployment..."
required_files=(
    "render.yaml"
    "requirements.txt"
    "app/main.py"
    "app/config.py"
    "DEPLOYMENT_GUIDE.md"
    ".env.render"
    "test_render_deployment.py"
    "pre_deployment_check.py"
)

all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ Missing: $file"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = false ]; then
    echo ""
    echo "❌ Some required files are missing. Please run the Copilot deployment setup first."
    exit 1
fi

echo ""
echo "✅ All required files present!"

# Check for .env file (should not be committed)
if [ -f ".env" ]; then
    echo ""
    echo "⚠️  Found .env file - this should NOT be committed to GitHub"
    echo "   Creating .gitignore to exclude it..."
    
    # Create or update .gitignore
    touch .gitignore
    if ! grep -q "^\.env$" .gitignore; then
        echo ".env" >> .gitignore
        echo "✅ Added .env to .gitignore"
    fi
    
    # Add other common exclusions
    exclusions=(
        "__pycache__/"
        "*.pyc"
        "*.pyo"
        "*.db"
        "logs/"
        "app/ml/models/*.pkl"
        "app/ml/models/*.joblib"
        ".DS_Store"
        "venv/"
        "env/"
    )
    
    for exclusion in "${exclusions[@]}"; do
        if ! grep -q "^$exclusion$" .gitignore; then
            echo "$exclusion" >> .gitignore
        fi
    done
    echo "✅ Updated .gitignore with common exclusions"
fi

# Add all files to git
echo ""
echo "📦 Staging files for commit..."
git add .

# Check what will be committed
echo ""
echo "📋 Files to be committed:"
git diff --cached --name-only

# Show current status
echo ""
echo "📊 Git status:"
git status --short

# Offer to commit
echo ""
read -p "🤔 Do you want to commit these changes? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "💾 Committing changes..."
    git commit -m "feat: Render deployment configuration

- Add render.yaml for Render service configuration
- Update config.py for automatic Render environment detection
- Enhance health checks for production monitoring
- Add deployment guide and testing scripts
- Configure production-ready CORS settings
- Ready for PostgreSQL database on Render"
    
    echo "✅ Changes committed!"
    
    # Check for remote origin
    if git remote get-url origin >/dev/null 2>&1; then
        echo ""
        echo "🌐 Remote origin detected:"
        git remote get-url origin
        echo ""
        read -p "🚀 Do you want to push to GitHub? (y/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "📤 Pushing to GitHub..."
            git push -u origin main
            echo "✅ Pushed to GitHub!"
        fi
    else
        echo ""
        echo "⚠️  No remote origin set. You'll need to:"
        echo "   1. Create a repository on GitHub"
        echo "   2. Add remote: git remote add origin https://github.com/USERNAME/REPO.git"
        echo "   3. Push: git push -u origin main"
    fi
else
    echo "⏭️  Skipping commit. You can commit later with:"
    echo "   git commit -m 'Add Render deployment configuration'"
fi

# Final checklist
echo ""
echo "=========================================================="
echo "🎯 DEPLOYMENT READINESS CHECKLIST:"
echo "=========================================================="
echo "✅ All required files created"
echo "✅ Git repository prepared"
echo "✅ .gitignore configured"

if [[ $REPLY =~ ^[Yy]$ ]] && git remote get-url origin >/dev/null 2>&1; then
    echo "✅ Code committed and pushed to GitHub"
else
    echo "🔲 Push code to GitHub (manual step required)"
fi

echo "🔲 Create Render account (render.com)"
echo "🔲 Create PostgreSQL database on Render"
echo "🔲 Create web service on Render"
echo "🔲 Configure environment variables"
echo "🔲 Test deployment"

echo ""
echo "📖 NEXT STEPS:"
echo "1. 📚 Read DEPLOYMENT_GUIDE.md for detailed instructions"
echo "2. 🌐 Push to GitHub if not done automatically"
echo "3. 🚀 Follow the Render deployment guide"
echo "4. 🧪 Test with test_render_deployment.py"
echo ""
echo "⏱️  Estimated time to production: 40 minutes"
echo "🎉 Your IoT + ML backend will be live on the internet!"
