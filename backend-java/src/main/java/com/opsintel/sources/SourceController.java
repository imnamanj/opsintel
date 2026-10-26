package com.opsintel.sources;

import java.util.List;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/sources")
public class SourceController {

    private final SourceService sourceService;

    public SourceController(SourceService sourceService) {
        this.sourceService = sourceService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public SourceResponse upload(Authentication authentication,
                                 @RequestParam("file") MultipartFile file) {
        return sourceService.upload(currentUser(authentication), file);
    }

    @GetMapping
    public List<SourceResponse> list(Authentication authentication) {
        return sourceService.list(currentUser(authentication));
    }

    @GetMapping("/{id}")
    public SourceResponse get(Authentication authentication, @PathVariable UUID id) {
        return sourceService.get(currentUser(authentication), id);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(Authentication authentication, @PathVariable UUID id) {
        sourceService.delete(currentUser(authentication), id);
    }

    private UUID currentUser(Authentication authentication) {
        return UUID.fromString(authentication.getName());
    }
}