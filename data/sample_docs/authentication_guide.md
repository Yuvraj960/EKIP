# Authentication & Authorization Guide

## Overview
EKIP uses token-based authentication built on the OAuth 2.0 framework with JSON Web Tokens (JWT). All requests to protected API endpoints must include a valid bearer token in the `Authorization` header.

## OAuth2 Flow
The authentication flow uses the Authorization Code Grant with PKCE (Proof Key for Code Exchange) for client applications.

1. **Authorization Request**: The client directs the user to `/oauth/authorize` with `client_id`, `redirect_uri`, `response_type=code`, `code_challenge`, and `code_challenge_method=S256`.
2. **Consent & Login**: The user authenticates against the identity provider and grants requested scopes.
3. **Authorization Code**: The authorization server redirects back to `redirect_uri` with an authorization code valid for 5 minutes.
4. **Token Exchange**: The client sends a `POST` request to `/oauth/token` containing the `code`, `client_id`, and `code_verifier`.
5. **Token Issuance**: The server returns an access token and a refresh token.

## Token Specifications
- **Access Token**: Signed JWT using RS256 algorithm. Validity period is 60 minutes (3600 seconds). Contains claims: `sub` (user ID), `iss` (issuer URL), `aud` (audience), `exp` (expiration timestamp), and `roles` (assigned RBAC roles).
- **Refresh Token**: Opaque cryptographically random 256-bit string. Validity period is 30 days with sliding window expiration. Stored in encrypted database table.

## Token Validation & Middleware
Every incoming API request is intercepted by the authentication middleware:
- Verifies JWT signature using the public keys from `/oauth/jwks.json`.
- Checks that `exp` is in the future (with 30-second clock skew tolerance).
- Verifies that `iss` matches `https://auth.ekip.internal`.
- Extracts user context and attaches it to request state for downstream handlers.

## API Key Authentication for Service-to-Service
Internal microservices communicate using API keys instead of user tokens:
- Header: `X-API-Key: <service_key>`
- Key format: `ekip_live_<32_random_alphanumeric_chars>`
- Rotation policy: Service keys must be rotated every 90 days. Old keys remain valid for a 24-hour grace period during rotation.
