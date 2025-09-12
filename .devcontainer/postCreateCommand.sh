// .devcontainer/postCreateCommand.sh
// This script runs after the Codespace is created.

#!/usr/bin/env bash
set -euo pipefail

# Install Python and Node dependencies
make install

# Ensure .env exists
if [ ! -f .env ]; then
  cp env/dev.example .env
fi

# Install Node.js 22 if not present
if ! command -v node >/dev/null || [ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 22 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

# Build Tailwind CSS
npm install
npm run build

# Apply migrations
python manage.py migrate

# Start dev server and CSS watcher
make dev
