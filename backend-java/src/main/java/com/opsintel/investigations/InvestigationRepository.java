package com.opsintel.investigations;

import java.util.Optional;
import java.util.UUID;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InvestigationRepository extends JpaRepository<Investigation, UUID> {

    Page<Investigation> findByUserId(UUID userId, Pageable pageable);

    Optional<Investigation> findByIdAndUserId(UUID id, UUID userId);
}