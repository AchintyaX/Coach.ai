import os
import requests
from dotenv import load_dotenv, dotenv_values
from pathlib import Path

REQUIRED_SCOPES = 'profile:read_all,activity:read_all,activity:read'
REDIRECT_URI = 'http://localhost'  # Must match one configured in Strava App settings
env_path = Path(__file__).resolve().parent.parent / '.env'

def prompt_user(question: str) -> str:
    return input(question).strip()

def load_env():
    if env_path.exists():
        return dotenv_values(env_path)
    else:
        print('.env file not found or not readable. Will prompt for all values.')
        return {}

def update_env_file(tokens: dict):
    env_content = ''
    if env_path.exists():
        with open(env_path, 'r') as file:
            env_content = file.read()

    lines = env_content.splitlines()
    new_lines = []
    access_token_updated = False
    refresh_token_updated = False

    for line in lines:
        if line.startswith('STRAVA_ACCESS_TOKEN='):
            new_lines.append(f"STRAVA_ACCESS_TOKEN={tokens['access_token']}")
            access_token_updated = True
        elif line.startswith('STRAVA_REFRESH_TOKEN='):
            new_lines.append(f"STRAVA_REFRESH_TOKEN={tokens['refresh_token']}")
            refresh_token_updated = True
        elif line.strip():
            new_lines.append(line)

    if not access_token_updated:
        new_lines.append(f"STRAVA_ACCESS_TOKEN={tokens['access_token']}")
    if not refresh_token_updated:
        new_lines.append(f"STRAVA_REFRESH_TOKEN={tokens['refresh_token']}")

    with open(env_path, 'w') as file:
        file.write('\n'.join(new_lines).strip() + '\n')
    print('✅ Tokens successfully saved to .env file.')

def main():
    print('--- Strava API Token Setup ---')

    existing_env = load_env()
    client_id = existing_env.get('STRAVA_CLIENT_ID')
    client_secret = existing_env.get('STRAVA_CLIENT_SECRET')

    if not client_id:
        client_id = prompt_user('Enter your Strava Application Client ID: ')
        if not client_id:
            print('❌ Client ID is required.')
            exit(1)
    else:
        print(f"ℹ️ Using Client ID from .env: {client_id}")

    if not client_secret:
        client_secret = prompt_user('Enter your Strava Application Client Secret: ')
        if not client_secret:
            print('❌ Client Secret is required.')
            exit(1)
    else:
        print('ℹ️ Using Client Secret from .env.')

    auth_url = (
        f"https://www.strava.com/oauth/authorize?client_id={client_id}"
        f"&response_type=code&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=force&scope={REQUIRED_SCOPES}"
    )

    print('\nStep 1: Authorize Application')
    print('Please visit the following URL in your browser:')
    print(f"\n{auth_url}\n")
    print(f"After authorizing, Strava will redirect you to {REDIRECT_URI}.")
    print("Copy the 'code' value from the URL in your browser's address bar.")
    print("(e.g., http://localhost/?state=&code=THIS_PART&scope=...)")

    auth_code = prompt_user('\nPaste the authorization code here: ')

    if not auth_code:
        print('❌ Authorization code is required.')
        exit(1)

    print('\nStep 2: Exchanging code for tokens...')

    try:
        response = requests.post('https://www.strava.com/oauth/token', data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
        })
        response.raise_for_status()
        data = response.json()

        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        expires_at = data.get('expires_at')

        if not access_token or not refresh_token:
            raise ValueError('Failed to retrieve tokens from Strava.')

        print('\n✅ Successfully obtained tokens!')
        print(f"Access Token: {access_token}")
        print(f"Refresh Token: {refresh_token}")
        print(f"Access Token Expires At: {expires_at}")

        save = prompt_user('\nDo you want to save these tokens to your .env file? (yes/no): ')

        if save.lower() in ['yes', 'y']:
            update_env_file({'access_token': access_token, 'refresh_token': refresh_token})

            # Optionally save client_id and client_secret if they weren't in .env initially
            env_content = ''
            if env_path.exists():
                with open(env_path, 'r') as file:
                    env_content = file.read()

            needs_update = False
            if 'STRAVA_CLIENT_ID=' not in env_content:
                env_content = f"STRAVA_CLIENT_ID={client_id}\n" + env_content
                needs_update = True
            if 'STRAVA_CLIENT_SECRET=' not in env_content:
                env_content = f"STRAVA_CLIENT_SECRET={client_secret}\n" + env_content
                needs_update = True

            if needs_update:
                with open(env_path, 'w') as file:
                    file.write(env_content.strip() + '\n')
                print('ℹ️ Client ID and Secret also saved/updated in .env.')

        else:
            print('\nTokens not saved. Please store them securely yourself.')

    except requests.RequestException as e:
        print('\n❌ Error exchanging code for tokens:')
        print(e)
        exit(1)

if __name__ == '__main__':
    main()
