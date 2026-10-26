package com.opsintel.sources;

import java.time.Instant;
import java.util.UUID;

public record SourceResponse(
        UUID id,
        String name,
        String type,
        String status,
        long sizeBytes,
        String checksum,
        Instant createdAt) {

    public static SourceResponse from(Source s) {
        return new SourceResponse(s.getId(), s.getName(), s.getType(), s.getStatus(),
                s.getSizeBytes(), s.getChecksum(), s.getCreatedAt());
    }
}