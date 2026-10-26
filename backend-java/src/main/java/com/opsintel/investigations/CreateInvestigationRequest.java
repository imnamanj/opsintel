package com.opsintel.investigations;

import java.util.List;
import java.util.UUID;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record CreateInvestigationRequest(
        @NotBlank @Size(max = 2000) String question,
        @NotEmpty @Size(max = 20) List<@NotNull UUID> sourceIds) {
}