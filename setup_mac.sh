#!/bin/bash

# Step 1: Install Homebrew if not already installed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Step 2: Install required system dependencies
echo "Installing system dependencies..."
brew install git curl python3 elan

# Step 3: Install Lean 4 via elan
echo "Installing Lean 4..."
elan toolchain install leanprover/lean4:stable
elan default leanprover/lean4:stable

# Step 4: Verify Lean installation
echo "Verifying Lean installation..."
lean --version

# Step 5: Install Python dependencies
echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install openai numpy scipy scikit-learn nltk tiktoken

# Step 6: Navigate to your project directory (replace with actual path)
cd /Users/jkarbowski/Documents/Lean/berkeley_mooc

echo "Setup complete! Now run 'lake lean Lean4CodeGenerator.lean' to verify."