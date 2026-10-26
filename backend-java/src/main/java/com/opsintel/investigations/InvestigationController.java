package com.opsintel.investigations;

import java.util.List;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/v1/investigations")
public class InvestigationController {

    private final InvestigationService service;

    public InvestigationController(InvestigationService service) {
        this.service = service;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public InvestigationResponse create(Authentication authentication,
                                        @Valid @RequestBody CreateInvestigationRequest request) {
        return service.create(currentUser(authentication), request);
    }

    @GetMapping("/{id}")
    public InvestigationResponse get(Authentication authentication, @PathVariable UUID id) {
        return service.get(currentUser(authentication), id);
    }

    @GetMapping
    public List<InvestigationResponse> list(Authentication authentication,
                                            @RequestParam(defaultValue = "0") int page,
                                            @RequestParam(defaultValue = "10") int size) {
        return service.list(currentUser(authentication), page, size);
    }

    private UUID currentUser(Authentication authentication) {
        return UUID.fromString(authentication.getName());
    }
}