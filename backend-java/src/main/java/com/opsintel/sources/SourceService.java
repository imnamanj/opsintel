package com.opsintel.sources;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@Service
public class SourceService {

    private static final Set<String> ALLOWED_TYPES = Set.of("PDF", "TXT", "CSV");
    private static final long MAX_BYTES = 20L * 1024 * 1024;

    private final SourceRepository repository;
    private final Path storageRoot;

    public SourceService(SourceRepository repository,
                         @Value("${app.storage.dir}") String storageDir) {
        this.repository = repository;
        this.storageRoot = Paths.get(storageDir).toAbsolutePath().normalize();
    }

    public SourceResponse upload(UUID ownerId, MultipartFile file) {
        // 1. File khaali to nahi?
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "File is empty");
        }

        // 2. Type check (sirf PDF, TXT, CSV)
        String originalName = cleanName(file.getOriginalFilename());
        String type = extensionOf(originalName);
        if (!ALLOWED_TYPES.contains(type)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "Only PDF, TXT and CSV files are allowed");
        }

        // 3. Size check
        if (file.getSize() > MAX_BYTES) {
            throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "File exceeds 20 MB");
        }

        try {
            // PDF asli PDF hai ya sirf naam badla hai?
            if (type.equals("PDF") && !looksLikePdf(file)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                        "File content is not a valid PDF");
            }

            // 4. Fingerprint (checksum)
            String checksum = sha256(file);

            // 5. Duplicate check
            if (repository.existsByOwnerIdAndChecksum(ownerId, checksum)) {
                throw new ResponseStatusException(HttpStatus.CONFLICT,
                        "This file has already been uploaded");
            }

            // 6. File disk par save karo (naam random UUID, user ka diya naam nahi)
            String storageKey = ownerId + "/" + UUID.randomUUID() + "." + type.toLowerCase(Locale.ROOT);
            Path target = storageRoot.resolve(storageKey).normalize();
            if (!target.startsWith(storageRoot)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid file path");
            }
            Files.createDirectories(target.getParent());
            try (InputStream in = file.getInputStream()) {
                Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
            }

            // 7. Database row save karo
            Source source = new Source();
            source.setOwnerId(ownerId);
            source.setName(originalName);
            source.setType(type);
            source.setStorageKey(storageKey);
            source.setSizeBytes(file.getSize());
            source.setChecksum(checksum);
            try {
                return SourceResponse.from(repository.save(source));
            } catch (DataIntegrityViolationException e) {
                Files.deleteIfExists(target);
                throw new ResponseStatusException(HttpStatus.CONFLICT,
                        "This file has already been uploaded");
            }
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "Could not store the file");
        }
    }

    public List<SourceResponse> list(UUID ownerId) {
        return repository.findByOwnerIdOrderByCreatedAtDesc(ownerId).stream()
                .map(SourceResponse::from)
                .toList();
    }

    public SourceResponse get(UUID ownerId, UUID id) {
        return SourceResponse.from(find(ownerId, id));
    }

    public void delete(UUID ownerId, UUID id) {
        Source source = find(ownerId, id);
        try {
            Files.deleteIfExists(storageRoot.resolve(source.getStorageKey()).normalize());
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "Could not delete the file");
        }
        repository.delete(source);
    }

    private Source find(UUID ownerId, UUID id) {
        return repository.findByIdAndOwnerId(id, ownerId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Source not found"));
    }

    private String cleanName(String name) {
        if (name == null || name.isBlank()) {
            return "unnamed";
        }
        String justName = name.replace("\\", "/");
        justName = justName.substring(justName.lastIndexOf('/') + 1).trim();
        if (justName.isEmpty()) {
            return "unnamed";
        }
        return justName.length() > 255 ? justName.substring(justName.length() - 255) : justName;
    }

    private String extensionOf(String name) {
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot + 1).toUpperCase(Locale.ROOT);
    }

    private boolean looksLikePdf(MultipartFile file) throws IOException {
        try (InputStream in = file.getInputStream()) {
            byte[] head = in.readNBytes(5);
            return head.length == 5 && new String(head, StandardCharsets.ISO_8859_1).equals("%PDF-");
        }
    }

    private String sha256(MultipartFile file) throws IOException {
        try (InputStream in = file.getInputStream()) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] buffer = new byte[8192];
            int read;
            while ((read = in.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }
}