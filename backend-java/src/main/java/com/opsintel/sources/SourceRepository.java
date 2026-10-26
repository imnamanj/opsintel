package com.opsintel.sources;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

public interface SourceRepository extends JpaRepository<Source, UUID> {

    List<Source> findByOwnerIdOrderByCreatedAtDesc(UUID ownerId);

    Optional<Source> findByIdAndOwnerId(UUID id, UUID ownerId);

    boolean existsByOwnerIdAndChecksum(UUID ownerId, String checksum);
}