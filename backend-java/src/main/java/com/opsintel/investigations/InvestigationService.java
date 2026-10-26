package com.opsintel.investigations;

import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import com.opsintel.sources.Source;
import com.opsintel.sources.SourceRepository;

@Service
public class InvestigationService {

    private static final int MAX_PAGE_SIZE = 50;

    private final InvestigationRepository investigations;
    private final SourceRepository sources;

    public InvestigationService(InvestigationRepository investigations, SourceRepository sources) {
        this.investigations = investigations;
        this.sources = sources;
    }

    @Transactional
    public InvestigationResponse create(UUID userId, CreateInvestigationRequest request) {
        // 1. Duplicate file ids hata do
        Set<UUID> ids = new LinkedHashSet<>(request.sourceIds());

        // 2 and 3. Saari files mili? Aur sab isi user ki hain?
        List<Source> found = sources.findAllById(ids);
        boolean allOwned = found.size() == ids.size()
                && found.stream().allMatch(s -> s.getOwnerId().equals(userId));
        if (!allOwned) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Source not found");
        }

        // 4 and 5. Ticket banao aur save karo
        Investigation investigation = new Investigation();
        investigation.setUserId(userId);
        investigation.setQuestion(request.question().trim());
        investigation.setSourceIds(new HashSet<>(ids));
        return InvestigationResponse.from(investigations.save(investigation));
    }

    public InvestigationResponse get(UUID userId, UUID id) {
        Investigation investigation = investigations.findByIdAndUserId(id, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Investigation not found"));
        return InvestigationResponse.from(investigation);
    }

    public List<InvestigationResponse> list(UUID userId, int page, int size) {
        int safePage = Math.max(page, 0);
        int safeSize = Math.min(Math.max(size, 1), MAX_PAGE_SIZE);
        PageRequest pageable = PageRequest.of(safePage, safeSize, Sort.by(Sort.Direction.DESC, "createdAt"));
        return investigations.findByUserId(userId, pageable)
                .map(InvestigationResponse::from)
                .getContent();
    }
}