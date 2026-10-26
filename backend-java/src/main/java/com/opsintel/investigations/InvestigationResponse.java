package com.opsintel.investigations;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record InvestigationResponse(
        UUID investigationId,
        String question,
        String status,
        List<UUID> sourceIds,
        Instant createdAt) {

    public static InvestigationResponse from(Investigation i) {
        return new InvestigationResponse(
                i.getId(),
                i.getQuestion(),
                i.getStatus(),
                i.getSourceIds().stream().sorted().toList(),
                i.getCreatedAt());
    }
}