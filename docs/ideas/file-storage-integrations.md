# Generic File Storage Integrations

## Status
Idea - Not Started

## Problem
Currently documents are stored via Paperless-ngx. Some users may want direct file storage without a document management system, or use different storage backends.

## Proposed Integrations

### S3-Compatible Storage
- AWS S3
- MinIO
- Backblaze B2
- DigitalOcean Spaces

### WebDAV
- Nextcloud
- ownCloud
- Generic WebDAV servers

### Local File System
- Direct folder storage
- Useful for simple deployments

## Use Cases
- Store expense receipts without Paperless
- Backup generated reports to cloud storage
- Export event data to shared folders

## Implementation Notes

### Provider Interface
```python
class FileStorageProvider(IntegrationProvider):
    async def upload(self, path: str, content: bytes) -> str
    async def download(self, path: str) -> bytes
    async def list(self, prefix: str) -> list[str]
    async def delete(self, path: str) -> bool
```

### Configuration
- Storage type selection
- Credentials (access key, secret, etc.)
- Bucket/container name
- Path prefix

## Reference
- REQUIREMENTS.md line 247

## Related
- Paperless-ngx integration (existing document provider)
- Backup/restore functionality
