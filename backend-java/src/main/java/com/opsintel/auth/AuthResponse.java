package com.opsintel.auth;

public record AuthResponse(String token, String tokenType, long expiresInSeconds) {
}