# Docker Security Hardening

This document outlines the security hardening measures implemented for the WireGuard Mesh Manager Docker containers.

## Container Security Measures

### 1. Minimal Base Images

- **Backend**: `python:3.11-slim` - Reduced attack surface vs full Python images
- **Frontend**: `node:20-alpine` - Small footprint and minimal packages
- Multi-stage builds for production to remove build-time dependencies

### 2. Non-Root User Execution

- All containers run as non-root user `wmm` (UID/GID: 1001)
- Dedicated user group isolation
- Proper file permissions set (700 on sensitive directories)

### 3. Filesystem Security

- **Read-only filesystem**: Prevents unauthorized modifications
- **tmpfs mounts**: Temporary directories mounted with `noexec,nosuid`
- **Secure permissions**: Data directories with 700 permissions
- **Attack surface reduction**: Removed man pages, docs, and unnecessary files

### 4. Runtime Security

- **Capability dropping**: All capabilities dropped except essential ones (`CHOWN`, `SETGID`, `SETUID`)
- **Seccomp profiles**: Default secure computing mode enabled
- **No new privileges**: Prevents privilege escalation
- **Resource limits**: CPU, memory, PIDs, and file descriptor limits
- **Process isolation**: PID and user namespace restrictions

### 5. Network Security

- **Localhost binding**: Services only bind to `127.0.0.1`
- **Custom networks**: Isolated Docker networks with specific subnets
- **IPv6 disabled**: Reduces attack surface
- **DNS hardening**: Using trusted DNS servers in production

### 6. Process Management

- **dumb-init**: Proper PID 1 process handling and signal forwarding
- **Health checks**: Container health monitoring and automatic restart
- **Graceful shutdown**: Proper signal handling for clean shutdowns

### 7. Environment Hardening

- **Python**: `PYTHONOPTIMIZE=2`, `PYTHONNOUSERSITE=1`, random hash seed
- **Node.js**: Production optimizations, telemetry disabled, memory limits
- **No development tools**: Build tools removed from production images

### 8. Dependency Security

- **Package cleanup**: Cache cleared after installation
- **Minimal packages**: Only necessary runtime dependencies installed
- **CA certificates**: Proper SSL/TLS certificate handling
- **Vulnerability scanning**: Labels for automated security scanning

## Docker Compose Security

### Development Environment

```yaml
security_opt:
  - no-new-privileges:true
  - seccomp:default
read_only: true
tmpfs:
  - /tmp:noexec,nosuid,size=100m
  - /var/tmp:noexec,nosuid,size=100m
  - /run:noexec,nosuid,size=50m
cap_drop:
  - ALL
cap_add:
  - CHOWN
  - SETGID
  - SETUID
```

### Production Environment

- **AppArmor**: Additional security profiles
- **Stricter limits**: Lower resource limits for production
- **Enhanced monitoring**: Longer health check intervals
- **Volume security**: Read-only mounts where possible

## Security Best Practices Implemented

1. **Principle of Least Privilege**: Containers have minimal required permissions
2. **Defense in Depth**: Multiple layers of security controls
3. **Immutable Infrastructure**: Read-only filesystems and minimal runtime modifications
4. **Secure by Default**: Security settings applied without requiring configuration
5. **Auditability**: Security labels and proper metadata for scanning tools

## Ongoing Security Maintenance

- Regular base image updates
- Dependency vulnerability scanning
- Security policy reviews
- Container runtime monitoring
- Log analysis and incident response

## Compliance Notes

These hardening measures help with:

- CIS Docker Benchmark compliance
- NIST Cybersecurity Framework
- Industry security standards
- Container security best practices

## Monitoring and Alerting

Set up monitoring for:

- Container privilege escalations
- Unusual file system modifications
- Resource limit violations
- Failed health checks
- Security policy violations
