import os
import subprocess
import sys
from pathlib import Path

# Paths
PLUGIN_DIR = Path(__file__).parent.resolve()
VERCEL_DIR = PLUGIN_DIR.parent / "Vercel_website"
ENV_FILE = PLUGIN_DIR / ".env"

def main():
    print("🤖 AI Salesman Vercel Auto-Updater")
    print("-" * 40)
    
    if not VERCEL_DIR.exists():
        print(f"❌ Error: Vercel website directory not found at {VERCEL_DIR}")
        sys.exit(1)
        
    if not ENV_FILE.exists():
        print(f"❌ Error: .env file not found at {ENV_FILE}")
        sys.exit(1)

    # 1. Read the ngrok URL from .env
    ngrok_url = None
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("PUBLIC_API_URL="):
                ngrok_url = line.split("=", 1)[1].strip().strip("'").strip('"')
                break
                
    if not ngrok_url:
        print("❌ Error: Could not find PUBLIC_API_URL in .env file.")
        print("Make sure you have run 'python run.py' first!")
        sys.exit(1)
        
    print(f"✅ Found new Ngrok URL: {ngrok_url}")
    
    # 2. Update Vercel Environment Variable
    print("\n🔄 Updating Vercel Environment Variable...")
    try:
        # Remove old variable
        print("   - Removing old SHOPBOT_API_URL...")
        subprocess.run(
            ["npx.cmd", "-y", "vercel", "env", "rm", "SHOPBOT_API_URL", "production", "--yes"],
            cwd=str(VERCEL_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Add new variable (using shell=True so we can pipe the echo)
        print("   - Adding new SHOPBOT_API_URL...")
        cmd = f'echo {ngrok_url} | npx -y vercel env add SHOPBOT_API_URL production'
        result = subprocess.run(
            cmd,
            cwd=str(VERCEL_DIR),
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("❌ Failed to add environment variable:")
            print(result.stderr)
            sys.exit(1)
            
        print("✅ Environment variable updated successfully!")
    except Exception as e:
        print(f"❌ Error updating environment variable: {e}")
        sys.exit(1)

    # 3. Redeploy Vercel Site
    print("\n🚀 Redeploying Vercel Site (this may take a minute)...")
    try:
        result = subprocess.run(
            ["npx.cmd", "-y", "vercel", "deploy", "--prod", "--yes"],
            cwd=str(VERCEL_DIR),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Deployment successful!")
            # Extract deployment URL if possible
            for line in result.stderr.splitlines() + result.stdout.splitlines():
                if line.startswith("https://"):
                    print(f"\n🎉 Your site is live at: {line.strip()}")
                    break
        else:
            print("❌ Deployment failed:")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Error during deployment: {e}")

if __name__ == "__main__":
    main()
