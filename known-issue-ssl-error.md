# ClaudeSync SSL Certificate Issue - Troubleshooting Guide

## Error Description

```
Please enter your sessionKey:
Please enter the expires time for the sessionKey (optional) [Sun, 23 Mar 2025 10:44:48 UTC]:
2025-02-21 11:44:50,427 - ERROR - URL Error: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1020)>
API request failed: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1020)>
Failed to retrieve organizations. Please enter a valid sessionKey.
```

## Analysis

This error occurs because Python is unable to verify the SSL certificate when making requests to the Claude API. The specific issues are:

1. The error occurs in the login process when trying to validate the session key
2. It's specifically a certificate verification failure
3. This is a common issue with Python's SSL certificate handling, especially on some systems

## Solutions

Here are a few solutions to try, in order of recommendation:

### 1. Install certificates for Python (Recommended)

**For macOS users:**
```bash
cd /Applications/Python\ 3.10/  # Adjust version number as needed
./Install\ Certificates.command
```

**For Windows users:**
```bash
pip install --upgrade certifi
```

### 2. Update your certifi package

```bash
pip install --upgrade certifi
```

### 3. Temporarily disable SSL verification

**Note:** This is not recommended for production use.

**For Unix/Mac:**
```bash
export PYTHONHTTPSVERIFY=0
claudesync auth login
```

**For Windows:**
```bash
set PYTHONHTTPSVERIFY=0
claudesync auth login
```

## Follow-up

After implementing one of these solutions, try the login command again:
```bash
claudesync auth login
```

The first solution (installing certificates) is the most secure and recommended approach.

If using this in a development environment and needing a quick fix, you could modify the code to handle SSL verification differently, but fixing the certificate issue properly using one of the above methods is recommended.
